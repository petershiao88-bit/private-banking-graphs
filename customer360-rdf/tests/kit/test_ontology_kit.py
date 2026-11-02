"""ontology_kit：config、類別組成元件、版本控制、建置、OWL 推理與 agent context 發佈。"""

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

import yaml
from rdflib import Graph, URIRef
from rdflib.namespace import OWL

from ontology_kit import build, components, context, reasoning, release, versioning
from ontology_kit.config import Config

ROOT = Path(__file__).resolve().parents[2]
SEC = "https://example.org/ontology/securities#"
FH = "https://example.org/ontology/holding#"
BASELINE = str(ROOT / "legacy/archive/before-department-v0.16.0")


class KitTestCase(unittest.TestCase):
    def setUp(self):
        for key in [k for k in os.environ if k.startswith("C360_")]:
            patcher = mock.patch.dict(os.environ)
            patcher.start()
            self.addCleanup(patcher.stop)
            os.environ.pop(key)
        self.cfg = Config(ROOT / "config.yaml")

    def sandbox(self, edit_config=None, previous=None):
        """複製本體、PG 與設定到暫存資料夾。previous=None 時改用 v0.15.0 快照當比對基準。"""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        shutil.copy2(ROOT / "config.yaml", tmp / "config.yaml")
        shutil.copytree(ROOT / "ontology", tmp / "ontology")
        (tmp / "pg").mkdir()
        for pattern in ("*.json", "*.py"):
            for path in (ROOT / "pg").glob(pattern):
                shutil.copy2(path, tmp / "pg" / path.name)
        data = yaml.safe_load((tmp / "config.yaml").read_text(encoding="utf-8"))
        data["paths"]["previous_release"] = previous
        data["paths"]["baseline_sources"] = BASELINE
        if edit_config:
            edit_config(data)
        (tmp / "config.yaml").write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return tmp

    def bundle_graph(self, cfg):
        data = release.build_bundle(cfg, None).serialize(format="turtle", encoding="utf-8")
        return Graph().parse(data=data, format="turtle")


class ConfigTests(KitTestCase):
    def test_paths_are_relative_to_config_and_overridable_by_environment(self):
        self.assertEqual(self.cfg.root, ROOT)
        self.assertEqual(self.cfg.path_of("release_dir"), ROOT / "release")
        with mock.patch.dict(os.environ, {"C360_PATH_RELEASE_DIR": "/tmp/c360-release", "C360_PATH_PREVIOUS_RELEASE": "none"}):
            cfg = Config(ROOT / "config.yaml")
            self.assertEqual(cfg.path_of("release_dir"), Path("/tmp/c360-release"))
            self.assertIsNone(cfg.path_of("previous_release"))

    def test_every_module_is_in_the_catalog_and_exists(self):
        catalog = versioning.catalog_entries(self.cfg)
        for m in self.cfg.modules:
            self.assertTrue(m.path.is_file(), m.file)
            self.assertEqual((self.cfg.path_of("catalog").parent / catalog[m.iri]).resolve(), m.path)

    def test_external_evidence_paths_map_into_this_repository(self):
        path = self.cfg.external("Ontology/私銀智能問答/sources/sql/1.AUM_DETAIL.sql")
        self.assertEqual(path, self.cfg.path_of("evidence_root") / "sources/sql/1.AUM_DETAIL.sql")
        self.assertEqual(self.cfg.external("../../私銀智能問答/sources/metadata/AUM_metadata.xlsx"),
                         self.cfg.path_of("evidence_root") / "sources/metadata/AUM_metadata.xlsx")


class ComponentTests(KitTestCase):
    def test_all_classes_have_valid_components_per_layer(self):
        _, classes, properties, issues = components.build(self.cfg)
        self.assertEqual(issues, [])
        counts = {key: sum(c["layer"] == key for c in classes) for key in self.cfg.layers}
        self.assertEqual(counts, {"holding": 12, "bank": 24, "securities": 7})
        self.assertEqual((sum(p["kind"] == "object" for p in properties),
                          sum(p["kind"] == "datatype" for p in properties)), (9, 19))
        record = next(c for c in classes if c["uri"] == SEC + "SecuritiesAUM")
        self.assertEqual((record["governance_level"], record["subsidiary"], record["parents"], record["module"]),
                         ("子公司", "證券", [FH + "AUM"], "ontology/securities/metrics.ttl"))

    def test_missing_definition_and_subsidiary_class_not_reaching_holding_are_errors(self):
        tmp = self.sandbox()
        with open(tmp / "ontology/securities/products.ttl", "a", encoding="utf-8") as handle:
            handle.write('\n<https://example.org/ontology/securities#Orphan> a <http://www.w3.org/2002/07/owl#Class> ;'
                         ' <http://www.w3.org/2000/01/rdf-schema#label> "孤兒"@zh-TW ;'
                         ' <https://example.org/ontology/holding#governanceLevel> "子公司" ;'
                         ' <https://example.org/ontology/holding#subsidiary> "銀行" .\n')
        _, _, _, issues = components.build(Config(tmp / "config.yaml"))
        rules = {i["rule"] for i in issues if i["id"] == "securities:Orphan"}
        self.assertEqual(rules, {"definition", "subsidiary", "must_reach_layer"})

    def test_release_class_cannot_depend_on_lower_maturity_parent(self):
        def edit(data):
            for module in data["modules"]:
                module["maturity"] = "informative" if module["layer"] == "holding" else "release"
        _, _, _, issues = components.build(Config(self.sandbox(edit) / "config.yaml"))
        self.assertIn("maturity", {i["rule"] for i in issues})


class VersioningTests(KitTestCase):
    def test_every_version_and_maturity_touchpoint_matches_config(self):
        self.assertEqual(versioning.check(self.cfg), [])

    def test_mismatches_are_reported(self):
        tmp = self.sandbox()
        path = tmp / "pg/deposits.json"
        path.write_text(path.read_text(encoding="utf-8").replace(f'"ontology_version": "{self.cfg.version}"',
                                                                 '"ontology_version": "0.0.1"'), encoding="utf-8")
        problems = versioning.check(Config(tmp / "config.yaml"))
        self.assertEqual([(p["file"], p["field"]) for p in problems], [("pg/deposits.json", "ontology_version")])

    def test_v017_is_a_module_restructure_of_release_v016(self):
        _, classes, properties, _ = components.build(self.cfg, self.cfg.release_modules())
        result = versioning.diff(self.cfg, versioning.load_previous(self.cfg), classes, properties)
        self.assertEqual(result["previous"]["version"], "0.16.0")
        self.assertEqual(len(result["changes"]), 43 + 28)
        self.assertTrue(all(c["change"] == "modified" and set(c["fields"]) == {"module"} for c in result["changes"]))
        self.assertEqual((result["required"], result["gate"]), ("minor", []))

    def test_diff_against_v015_snapshot_shows_department_additions(self):
        cfg = Config(self.sandbox() / "config.yaml")
        _, classes, properties, _ = components.build(cfg)
        result = versioning.diff(cfg, versioning.load_previous(cfg), classes, properties)
        self.assertEqual({(c["change"], c["id"]) for c in result["changes"] if c["change"] != "modified"},
                         {("added", "fh:Department"), ("added", "bank:PrivateBankingDepartment"),
                          ("added", "fh:usesMetric")})
        self.assertEqual(result["gate"], [])

    def test_removal_requires_deprecation_in_previous_release(self):
        _, classes, properties, _ = components.build(self.cfg)
        ghost = dict(classes[0], uri=FH + "Ghost", id="fh:Ghost", deprecated=False)
        result = versioning.diff(self.cfg, ("0.15.0", classes + [ghost], properties, "test"), classes, properties)
        self.assertTrue(any("fh:Ghost" in g for g in result["gate"]))
        ghost["deprecated"] = True
        result = versioning.diff(self.cfg, ("0.15.0", classes + [ghost], properties, "test"), classes, properties)
        self.assertEqual(result["gate"], [])

    def test_changes_without_version_bump_are_blocked(self):
        _, classes, properties, _ = components.build(self.cfg)
        result = versioning.diff(self.cfg, (self.cfg.version, classes[1:], properties, "test"), classes, properties)
        self.assertIn("本體有變更但版號未升", result["gate"])

    def test_bump_then_release_end_to_end(self):
        tmp = self.sandbox()
        cfg = Config(tmp / "config.yaml")
        self.assertEqual(release.run(cfg)["status"], "created")
        current = cfg.version
        major, minor, _ = (int(x) for x in current.split("."))
        new = f"{major}.{minor + 1}.0"
        with self.assertRaises(ValueError):
            versioning.plan_bump(cfg, current, "2026-11-01")
        versioning.apply_edits(versioning.plan_bump(cfg, new, "2026-11-01"))
        bumped = Config(tmp / "config.yaml")
        self.assertEqual((bumped.version, bumped.date), (new, "2026-11-01"))
        self.assertEqual(bumped.path_of("previous_release"), tmp / f"release/{current}")
        self.assertEqual(versioning.check(bumped), [])
        self.assertIn(f'"{new}"', (tmp / "pg/build_cypher.py").read_text(encoding="utf-8"))
        crlf = [p.name for p in (ROOT / "pg").glob("*.json") if b"\r\n" in p.read_bytes()]
        for name in crlf:  # bump 保留原檔換行
            self.assertIn(b"\r\n", (tmp / "pg" / name).read_bytes(), name)
        result = release.run(bumped)
        self.assertEqual((result["status"], result["changes"]), ("created", 0))
        bundle = Graph().parse(tmp / f"release/{new}" / release.BUNDLE)
        self.assertIn((URIRef(bumped.ontology_uri), OWL.priorVersion, URIRef(f"{bumped.ontology_uri}/{current}")), bundle)
        self.assertEqual((tmp / "release/LATEST").read_text(encoding="utf-8").strip(), new)


class BuildTests(KitTestCase):
    def test_build_output_is_current_and_detects_stale_sources(self):
        self.assertEqual(build.check(self.cfg)["result"], "PASS")
        tmp = self.sandbox(previous=None)
        cfg = Config(tmp / "config.yaml")
        build.build(cfg)
        self.assertEqual(build.check(cfg)["result"], "PASS")
        with open(tmp / "ontology/holding/parties.ttl", "a", encoding="utf-8") as handle:
            handle.write('\n<https://example.org/ontology/holding#Customer> <http://www.w3.org/2000/01/rdf-schema#comment> "test" .\n')
        with self.assertRaises(build.StaleBuild):
            build.check(cfg)

    def test_unreleased_import_is_rejected(self):
        def edit(data):
            data["modules"] = [m for m in data["modules"] if m["file"] != "ontology/holding/annotations.ttl"]
        with self.assertRaises(release.ReleaseError):
            build.build(Config(self.sandbox(edit) / "config.yaml"))


class ReasoningTests(KitTestCase):
    def test_owlrl_matches_independent_walk_and_finds_seven_new_relations(self):
        report = reasoning.reason(self.bundle_graph(self.cfg), self.cfg)
        self.assertEqual((report["classes"], report["asserted_subclass_axioms"],
                          report["entailed_pairs"], report["inferred_only"]), (43, 37, 44, 7))
        inferred = {(self.cfg.curie(e["class"]), self.cfg.curie(e["ancestor"]))
                    for e in report["entailments"] if not e["asserted"]}
        self.assertIn(("securities:SecuritiesAUM", "fh:Metric"), inferred)
        self.assertIn(("bank:FinancialAdvisor", "fh:Employee"), inferred)
        self.assertEqual((report["cycles"], report["unsatisfiable"]), ([], []))

    def test_axioms_outside_whitelist_block_reasoning(self):
        graph = self.bundle_graph(self.cfg)
        extra = """@prefix owl: <http://www.w3.org/2002/07/owl#> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
        @prefix fh: <https://example.org/ontology/holding#> .
        fh:AUM owl:equivalentClass fh:LUM . fh:holds rdfs:subPropertyOf fh:serves . fh:someone a fh:Customer ."""
        graph.parse(data=extra, format="turtle")
        with self.assertRaises(reasoning.UnsupportedAxioms) as caught:
            reasoning.reason(graph, self.cfg)
        self.assertEqual(len(caught.exception.issues), 3)

    def test_deprecated_marker_is_accepted_by_reasoner(self):
        graph = self.bundle_graph(self.cfg)
        graph.parse(data='@prefix owl: <http://www.w3.org/2002/07/owl#> . @prefix fh: <https://example.org/ontology/holding#> .'
                         ' fh:LUM owl:deprecated true .', format="turtle")
        self.assertEqual(reasoning.reason(graph, self.cfg)["inferred_only"], 7)


class ContextTests(KitTestCase):
    def test_context_pack_carries_chains_rules_and_version(self):
        _, classes, properties, _ = components.build(self.cfg, self.cfg.release_modules())
        report = reasoning.reason(self.bundle_graph(self.cfg), self.cfg)
        pack = context.build(self.cfg, classes, properties, report, {"bundle_sha256": "0" * 64})
        item = next(c for c in pack["classes"] if c["id"] == "securities:SecuritiesAUM")
        self.assertEqual(item["chains"], ["證券 AUM ⊑ AUM ⊑ 指標"])
        self.assertEqual([r["id"] for r in item["inferred_ancestors"]], ["fh:Metric"])
        self.assertIn("fh:metricAmount", {p["id"] for p in item["inherited_properties"]})
        self.assertEqual(pack["usage_rules"], self.cfg.context["usage_rules"])
        markdown = context.render_markdown(pack)
        self.assertIn("上層鏈（含推理）：證券 AUM ⊑ AUM ⊑ 指標", markdown)
        self.assertIn(pack["release_iri"], markdown)


class ReleaseTests(KitTestCase):
    def test_current_release_is_published_and_reproducible(self):
        self.assertEqual(release.run(self.cfg, write=False)["status"], "unchanged")
        manifest = json.loads((self.cfg.release_dir() / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["modules"]), len(self.cfg.modules))

    def test_release_is_immutable(self):
        tmp = self.sandbox()
        self.assertEqual(release.run(Config(tmp / "config.yaml"))["status"], "created")
        self.assertEqual(release.run(Config(tmp / "config.yaml"))["status"], "unchanged")
        path = tmp / "ontology/holding/parties.ttl"
        path.write_text(path.read_text(encoding="utf-8").replace("集團業務中所服務的客戶。", "改過的定義。"), encoding="utf-8")
        with self.assertRaises(release.ReleaseError) as caught:
            release.run(Config(tmp / "config.yaml"))
        self.assertEqual(caught.exception.stage, "發佈")

    def test_unreleased_dependency_blocks_release(self):
        def edit(data):
            for module in data["modules"]:
                if module["layer"] == "holding":
                    module["maturity"] = "informative"
        tmp = self.sandbox(edit)
        for path in (tmp / "ontology/holding").glob("*.ttl"):  # 成熟度也寫在 TTL 內，兩邊一起改
            path.write_text(path.read_text(encoding="utf-8").replace("fibo-fnd-utl-av:Provisional",
                                                                     "fibo-fnd-utl-av:Informative"), encoding="utf-8")
        with self.assertRaises(release.ReleaseError) as caught:
            release.run(Config(tmp / "config.yaml"))
        self.assertIn(caught.exception.stage, {"類別組成元件驗證", "模組依賴檢查"})


if __name__ == "__main__":
    unittest.main()
