"""Import the repository's term-based ontology JSON into Neo4j.

Uses Neo4j's HTTP Query API and only Python's standard library. Set
NEO4J_PASSWORD in the environment before running this script.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


LABELS = (
    "Ontology", "Term", "SourceDocument", "MeasureLineage",
    "SqlEvidence", "Rule", "SourceProperty", "PhysicalTable",
    "PhysicalColumn", "ObjectTypeReference", "PropertyReference",
)


def graph_key(ontology_id: str, value: str) -> str:
    return f"{ontology_id}:{value}"


class Neo4j:
    def __init__(self, base_url: str, database: str, user: str, password: str):
        credentials = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.url = f"{base_url.rstrip('/')}/db/{database}/query/v2"
        self.headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        }

    def query(self, statement: str, parameters: dict | None = None) -> dict:
        body = json.dumps(
            {"statement": statement, "parameters": parameters or {}},
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(self.url, data=body, headers=self.headers, method="POST")
        try:
            with urlopen(request, timeout=60) as response:
                result = json.load(response)
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Neo4j HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"Cannot reach Neo4j at {self.url}: {exc}") from exc
        if result.get("errors"):
            raise RuntimeError(f"Neo4j query failed: {result['errors']}")
        return result

    def rows(self, statement: str, rows: list[dict], batch_size: int = 100) -> None:
        for start in range(0, len(rows), batch_size):
            self.query(statement, {"rows": rows[start:start + batch_size]})

    def count(self, statement: str, ontology_id: str) -> int:
        result = self.query(statement, {"ontologyId": ontology_id})
        return result["data"]["values"][0][0]


def prepare(document: dict, source_file: Path) -> tuple[str, dict[str, list[dict]]]:
    ontology = document["domain"]
    ontology_id = ontology["id"]
    if not ontology_id or not isinstance(document.get("terms"), list):
        raise ValueError("Expected domain.id and terms array")

    rows: dict[str, list[dict]] = {name: [] for name in (
        "sources", "terms", "lineages", "sql", "rules",
        "properties", "columns", "objects", "property_refs",
    )}
    rows["ontology"] = [{
        "key": ontology_id,
        "properties": {
            "id": ontology_id,
            "name": ontology.get("name"),
            "description": ontology.get("description"),
            "defaultDomain": ontology.get("defaultDomain"),
            "repositoryVersion": document.get("repositoryVersion"),
            "curationVersion": document.get("curationVersion"),
            "generationPolicy": document.get("generationPolicy"),
            "generatedAt": document.get("generatedAt"),
            "sourceFile": source_file.name,
            "sourceJson": json.dumps(ontology, ensure_ascii=False),
        },
    }]

    for source in document.get("sources", []):
        location = source.get("path") or source.get("url")
        if not location:
            continue
        rows["sources"].append({
            "key": graph_key(ontology_id, location),
            "ontologyKey": ontology_id,
            "properties": {"location": location, "role": source.get("role")},
        })

    seen_ids: set[str] = set()
    for term in document["terms"]:
        term_id = term["id"]
        if term_id in seen_ids:
            raise ValueError(f"Duplicate term ID: {term_id}")
        seen_ids.add(term_id)
        term_key = graph_key(ontology_id, term_id)
        evidence = term.get("evidence") or {}
        review = term.get("review") or {}
        curation = term.get("curation") or {}
        rows["terms"].append({
            "key": term_key,
            "ontologyKey": ontology_id,
            "properties": {
                "id": term_id,
                "ontologyId": ontology_id,
                "term": term.get("term"),
                "displayName": term.get("displayName"),
                "definition": term.get("definition"),
                "aliases": term.get("aliases") or [],
                "formula": term.get("formula"),
                "formulas": term.get("formulas") or [],
                "grain": term.get("grain") or [],
                "dimensionCandidates": term.get("dimensionCandidates") or [],
                "status": term.get("status"),
                "queryEnabled": term.get("queryEnabled"),
                "semanticOrigin": evidence.get("semanticOrigin"),
                "branchIndex": evidence.get("branchIndex"),
                "confirmedBy": review.get("confirmedBy"),
                "confirmedAt": review.get("confirmedAt"),
                "reviewComment": review.get("comment"),
                "curationApplied": curation.get("applied"),
                "overriddenFields": curation.get("overriddenFields") or [],
                "sourceJson": json.dumps(term, ensure_ascii=False),
            },
        })

        lineage = evidence.get("measureLineageId")
        if lineage:
            rows["lineages"].append({
                "termKey": term_key,
                "key": graph_key(ontology_id, lineage),
                "id": lineage,
            })
        for sql_id in evidence.get("sqlEvidenceIds") or []:
            rows["sql"].append({
                "termKey": term_key,
                "key": graph_key(ontology_id, sql_id),
                "id": sql_id,
            })
        for position, rule in enumerate(evidence.get("rules") or []):
            rule_hash = hashlib.sha256(rule.encode("utf-8")).hexdigest()
            rows["rules"].append({
                "termKey": term_key,
                "key": graph_key(ontology_id, rule_hash),
                "text": rule,
                "position": position,
            })
        for position, prop in enumerate(evidence.get("sourceProperties") or []):
            prop_key = graph_key(ontology_id, f"{term_id}:source:{position}")
            table = prop.get("physicalTable")
            column = prop.get("column")
            rows["properties"].append({
                "termKey": term_key,
                "key": prop_key,
                "properties": {
                    "ontologyId": ontology_id,
                    "position": position,
                    "physicalTable": table,
                    "column": column,
                    "objectTypeId": prop.get("objectTypeId"),
                    "propertyRef": prop.get("propertyRef"),
                    "mappingStatus": prop.get("mappingStatus"),
                    "sourceJson": json.dumps(prop, ensure_ascii=False),
                },
            })
            if table and column:
                rows["columns"].append({
                    "sourcePropertyKey": prop_key,
                    "tableKey": graph_key(ontology_id, table),
                    "columnKey": graph_key(ontology_id, f"{table}.{column}"),
                    "table": table,
                    "column": column,
                })
            if prop.get("objectTypeId"):
                rows["objects"].append({
                    "sourcePropertyKey": prop_key,
                    "key": graph_key(ontology_id, prop["objectTypeId"]),
                    "id": prop["objectTypeId"],
                })
            if prop.get("propertyRef"):
                rows["property_refs"].append({
                    "sourcePropertyKey": prop_key,
                    "key": graph_key(ontology_id, prop["propertyRef"]),
                    "id": prop["propertyRef"],
                })
    return ontology_id, rows


def import_graph(neo4j: Neo4j, ontology_id: str, rows: dict[str, list[dict]]) -> None:
    for label in LABELS:
        neo4j.query(
            f"CREATE CONSTRAINT ontology_{label.lower()}_key IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.key IS UNIQUE"
        )

    neo4j.rows("""
        UNWIND $rows AS row
        MERGE (n:Ontology {key: row.key})
        SET n += row.properties
    """, rows["ontology"])
    neo4j.rows("""
        UNWIND $rows AS row
        MATCH (o:Ontology {key: row.ontologyKey})
        MERGE (n:SourceDocument {key: row.key})
        SET n += row.properties
        MERGE (o)-[:HAS_SOURCE]->(n)
    """, rows["sources"])
    neo4j.rows("""
        UNWIND $rows AS row
        MATCH (o:Ontology {key: row.ontologyKey})
        MERGE (n:Term {key: row.key})
        SET n += row.properties
        MERGE (n)-[:IN_ONTOLOGY]->(o)
    """, rows["terms"])
    neo4j.rows("""
        UNWIND $rows AS row
        MATCH (t:Term {key: row.termKey})
        MERGE (n:MeasureLineage {key: row.key})
        SET n.id = row.id
        MERGE (t)-[:HAS_LINEAGE]->(n)
    """, rows["lineages"])
    neo4j.rows("""
        UNWIND $rows AS row
        MATCH (t:Term {key: row.termKey})
        MERGE (n:SqlEvidence {key: row.key})
        SET n.id = row.id
        MERGE (t)-[:SUPPORTED_BY_SQL]->(n)
    """, rows["sql"])
    neo4j.rows("""
        UNWIND $rows AS row
        MATCH (t:Term {key: row.termKey})
        MERGE (n:Rule {key: row.key})
        SET n.text = row.text
        MERGE (t)-[:HAS_RULE {position: row.position}]->(n)
    """, rows["rules"])
    neo4j.rows("""
        UNWIND $rows AS row
        MATCH (t:Term {key: row.termKey})
        MERGE (n:SourceProperty {key: row.key})
        SET n += row.properties
        MERGE (t)-[:HAS_SOURCE_PROPERTY]->(n)
    """, rows["properties"])
    neo4j.rows("""
        UNWIND $rows AS row
        MATCH (sp:SourceProperty {key: row.sourcePropertyKey})
        MERGE (tb:PhysicalTable {key: row.tableKey})
        SET tb.name = row.table
        MERGE (col:PhysicalColumn {key: row.columnKey})
        SET col.name = row.column, col.table = row.table
        MERGE (sp)-[:REFERS_TO_COLUMN]->(col)
        MERGE (col)-[:IN_TABLE]->(tb)
    """, rows["columns"])
    neo4j.rows("""
        UNWIND $rows AS row
        MATCH (sp:SourceProperty {key: row.sourcePropertyKey})
        MERGE (n:ObjectTypeReference {key: row.key})
        SET n.id = row.id
        MERGE (sp)-[:MAPPED_TO_OBJECT_TYPE]->(n)
    """, rows["objects"])
    neo4j.rows("""
        UNWIND $rows AS row
        MATCH (sp:SourceProperty {key: row.sourcePropertyKey})
        MERGE (n:PropertyReference {key: row.key})
        SET n.id = row.id
        MERGE (sp)-[:MAPPED_TO_PROPERTY]->(n)
    """, rows["property_refs"])

    checks = {
        "terms": (len(rows["terms"]), "MATCH (n:Term {ontologyId: $ontologyId}) RETURN count(n)"),
        "source properties": (len(rows["properties"]), "MATCH (n:SourceProperty {ontologyId: $ontologyId}) RETURN count(n)"),
        "SQL links": (len(set((r["termKey"], r["key"]) for r in rows["sql"])), "MATCH (t:Term {ontologyId: $ontologyId})-[:SUPPORTED_BY_SQL]->() RETURN count(*)"),
        "rule links": (len(rows["rules"]), "MATCH (t:Term {ontologyId: $ontologyId})-[:HAS_RULE]->() RETURN count(*)"),
    }
    for name, (expected, statement) in checks.items():
        actual = neo4j.count(statement, ontology_id)
        if actual != expected:
            raise RuntimeError(f"{name}: expected {expected}, found {actual}")
        print(f"{name}: {actual}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_file", type=Path)
    parser.add_argument("--url", default="http://127.0.0.1:7474")
    parser.add_argument("--database", default="neo4j")
    parser.add_argument("--user", default="neo4j")
    args = parser.parse_args()
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        parser.error("Set NEO4J_PASSWORD in the environment")
    path = args.json_file.resolve()
    document = json.loads(path.read_text(encoding="utf-8"))
    ontology_id, rows = prepare(document, path)
    client = Neo4j(args.url, args.database, args.user, password)
    import_graph(client, ontology_id, rows)
    print(f"Imported ontology {ontology_id} from {path.name}")


if __name__ == "__main__":
    main()
