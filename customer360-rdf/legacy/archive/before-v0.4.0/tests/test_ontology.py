import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ontology_builder", ROOT / "tools/build_ontology.py")
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
FH = Namespace("https://example.org/ontology/holding#")


class OntologyTests(unittest.TestCase):
    def setUp(self):
        self.graph = Graph().parse(ROOT / "holding-core.ttl", format="turtle")

    def test_exact_common_classes_and_inheritance(self):
        expected = {FH[name] for name in ("Customer", "FinancialProduct", "ContactInformation",
                                         "MobileContactInformation", "AddressContactInformation")}
        self.assertEqual(set(self.graph.subjects(RDF.type, OWL.Class)), expected)
        self.assertEqual(set(self.graph.subject_objects(RDFS.subClassOf)), {
            (FH.MobileContactInformation, FH.ContactInformation),
            (FH.AddressContactInformation, FH.ContactInformation),
        })

    def test_shared_properties_domains_and_ranges(self):
        fields = {"mobileNumber": FH.MobileContactInformation, **{
            name: FH.AddressContactInformation for name in
            ("countryCode", "city", "district", "addressLine", "postalCode", "fullAddress")}}
        self.assertEqual(set(self.graph.subjects(RDF.type, OWL.DatatypeProperty)),
                         {FH[name] for name in fields})
        for name, domain in fields.items():
            self.assertEqual(set(self.graph.objects(FH[name], RDFS.domain)), {domain})
            self.assertEqual(set(self.graph.objects(FH[name], RDFS.range)), {XSD.string})
        self.assertEqual(set(self.graph.subjects(RDF.type, OWL.ObjectProperty)),
                         {FH.holds, FH.hasContactPoint})
        for prop, target in ((FH.holds, FH.FinancialProduct),
                             (FH.hasContactPoint, FH.ContactInformation)):
            self.assertEqual(set(self.graph.objects(prop, RDFS.domain)), {FH.Customer})
            self.assertEqual(set(self.graph.objects(prop, RDFS.range)), {target})

    def test_no_company_or_department_terms_or_unapproved_axioms(self):
        for triple in self.graph:
            for term in triple:
                if isinstance(term, URIRef):
                    self.assertFalse(str(term).startswith(tuple(
                        "https://example.org/ontology/" + company
                        for company in ("bank", "securities", "life"))))
        forbidden = {OWL.sameAs, OWL.equivalentClass, OWL.equivalentProperty,
                     OWL.disjointWith, OWL.inverseOf, OWL.cardinality, OWL.minCardinality,
                     OWL.maxCardinality, OWL.hasKey, OWL.propertyChainAxiom}
        self.assertFalse(set(self.graph.predicates()) & forbidden)
        self.assertFalse(set(self.graph.subjects(RDF.type, OWL.NamedIndividual)))
        self.assertFalse(set(self.graph.subjects(RDF.type, OWL.FunctionalProperty)))
        self.assertFalse(set(self.graph.subjects(RDF.type, OWL.InverseFunctionalProperty)))
        self.assertNotIn(Literal("部門"), set(self.graph.objects(None, FH.governanceLevel)))

    def test_entities_have_concise_definitions_labels_and_governance(self):
        for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty):
            for entity in self.graph.subjects(RDF.type, kind):
                self.assertTrue(list(self.graph.objects(entity, RDFS.label)))
                self.assertTrue(list(self.graph.objects(entity, SKOS.definition)))
                self.assertEqual(set(self.graph.objects(entity, FH.governanceLevel)), {Literal("金控")})

    def test_catalog_targets_exist_and_versions_match(self):
        import xml.etree.ElementTree as ET
        entries = {n.attrib["name"]: n.attrib["uri"]
                   for n in ET.parse(ROOT / "catalog-v001.xml").getroot()}
        for uri, path in entries.items():
            graph = Graph().parse(ROOT / path, format="turtle")
            self.assertTrue((URIRef(uri), RDF.type, OWL.Ontology) in graph
                            or (None, OWL.versionIRI, URIRef(uri)) in graph)
        self.assertEqual(len(entries), 4)

    def test_current_exports_match_source(self):
        report = builder.check_outputs(ROOT)
        self.assertEqual(report["classes"], 5)
        self.assertEqual(report["data_properties"], 7)
        self.assertEqual(report["annotation_properties"], 5)
        self.assertEqual(report["full_owl_reasoner"], "not run")

    def test_no_retired_modules_active(self):
        for name in ("bank-contact.ttl", "securities-contact.ttl", "life-contact.ttl",
                     "bank-business-contact.ttl"):
            self.assertFalse((ROOT / name).exists())
            self.assertTrue((ROOT / "archive/before-v0.3.0" / name).is_file())
        self.assertEqual(set(json.loads((ROOT / "build-config.json").read_text(encoding="utf-8"))["sources"]),
                         {"holding-core.ttl"})

    def test_build_is_source_driven_and_detects_stale_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("holding-core.ttl", "build-config.json", "catalog-v001.xml"):
                shutil.copy2(ROOT / name, root / name)
            original_bytes = (root / "holding-core.ttl").read_bytes()
            builder.build(root)
            first = Graph().parse(root / "customer360-ontology.ttl", format="turtle")
            builder.build(root)
            self.assertTrue(isomorphic(first, Graph().parse(root / "customer360-ontology.ttl",
                                                           format="turtle")))
            self.assertEqual((root / "holding-core.ttl").read_bytes(), original_bytes)
            with (root / "holding-core.ttl").open("a", encoding="utf-8") as stream:
                stream.write('\nfh:Customer rdfs:comment "Test-only source change" .\n')
            with self.assertRaisesRegex(ValueError, "Stale"):
                builder.check_outputs(root)
            builder.build(root)
            self.assertIn((FH.Customer, RDFS.comment, Literal("Test-only source change")),
                          Graph().parse(root / "customer360-ontology.ttl", format="turtle"))

    def test_builder_rejects_unresolved_imports_and_source_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("holding-core.ttl", "build-config.json", "catalog-v001.xml"):
                shutil.copy2(ROOT / name, root / name)
            with (root / "holding-core.ttl").open("a", encoding="utf-8") as stream:
                stream.write('\n<https://example.org/ontology/holding> owl:imports <urn:missing> .\n')
            with self.assertRaisesRegex(ValueError, "Import must"):
                builder.expected_graph(root)
            config = json.loads((root / "build-config.json").read_text(encoding="utf-8"))
            config["outputs"]["turtle"] = "holding-core.ttl"
            (root / "build-config.json").write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                builder.expected_graph(root)
            with self.assertRaisesRegex(ValueError, "outside"):
                builder.local_file(root, "../outside.ttl")


if __name__ == "__main__":
    unittest.main()
