"""Run one HermiT classification in an isolated, timeout-controlled process."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    source = Path(args.input).resolve()
    if not source.is_relative_to(HERE):
        raise ValueError("Reasoning input must be inside the project")
    runtime = json.loads((HERE / "vendor/java-runtime.json").read_text(encoding="utf-8"))
    java = (HERE / runtime["java"]).resolve()
    if not java.is_relative_to(HERE / "vendor") or not java.is_file():
        raise ValueError("Project Java runtime missing")

    import owlready2
    from rdflib import Graph
    from rdflib.namespace import XSD

    owlready2.JAVA_EXE = str(java)
    started = time.monotonic()
    world = owlready2.World()
    # fileobj avoids Owlready2's file:///C:/ path handling on Windows.
    with source.open("rb") as handle:
        ontology = world.get_ontology("urn:customer360:reasoning:" + args.source_sha).load(fileobj=handle)
    classes = sorted(ontology.classes(), key=lambda cls: cls.iri)
    report = {
        "engine": "HermiT", "owlready2_version": str(owlready2.VERSION),
        "source_sha256": args.source_sha,
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "scope": "holding_and_subsidiary_owl_only", "pg_included": False,
        "classes": {}, "unsatisfiable_classes": [],
    }
    # xsd:date is outside HermiT's OWL 2 datatype map. Retain the axiom,
    # explicitly disclose ignored datatype semantics instead of rewriting it.
    rdf = Graph().parse(source, format="xml")
    unsupported = [str(XSD.date)] if any(rdf.triples((None, None, XSD.date))) else []
    report["unsupported_datatypes"] = unsupported
    report["consistency_complete"] = not unsupported
    report["limitations"] = ["HermiT 不檢查 xsd:date 的 datatype 語意；一致性檢查限於支援的語意範圍。"] if unsupported else []
    try:
        # This invokes the bundled HermiT Java process. No PG data is loaded.
        owlready2.sync_reasoner([ontology], infer_property_values=False, ignore_unsupported_datatypes=bool(unsupported), debug=0)
        report["consistent"] = True
        report["unsatisfiable_classes"] = sorted(cls.iri for cls in world.inconsistent_classes() if cls is not owlready2.Nothing)
        for cls in classes:
            report["classes"][cls.iri] = sorted(
                parent.iri for parent in cls.ancestors()
                if parent not in {cls, owlready2.Thing, owlready2.Nothing} and isinstance(parent, owlready2.ThingClass)
            )
    except owlready2.OwlReadyInconsistentOntologyError:
        report["consistent"] = False
    finally:
        world.close()
    report["duration_seconds"] = round(time.monotonic() - started, 3)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
