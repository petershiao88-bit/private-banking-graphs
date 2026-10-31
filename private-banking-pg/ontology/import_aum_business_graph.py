"""Add the reviewed AUM business layer to the imported Neo4j ontology graph.

The source JSON remains the technical evidence layer. The business dictionary
and staging registry define the metric/product hierarchy and SQL dependencies.
Set NEO4J_PASSWORD in the environment before running.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

from import_ontology_neo4j import Neo4j


LABELS = ("BusinessMetric", "ProductCategory", "StagingOutput", "CalculationRule", "BusinessDimension")


def key(kind: str, code: str) -> str:
    return f"aum:{kind}:{code}"


def load_inputs(dictionary_path: Path, ontology_path: Path, staging_path: Path):
    dictionary = json.loads(dictionary_path.read_text(encoding="utf-8"))
    ontology = json.loads(ontology_path.read_text(encoding="utf-8"))
    with staging_path.open(encoding="utf-8-sig", newline="") as handle:
        stages = list(csv.DictReader(handle))
    if dictionary["id"] != ontology["domain"]["id"] or dictionary["id"] != "aum":
        raise ValueError("Business dictionary and ontology IDs must both be aum")
    outputs = {row["staging_sql_id"]: row["output_object"] for row in stages}
    if len(outputs) != len(stages) or len(set(outputs.values())) != len(stages):
        raise ValueError("Staging SQL IDs and output objects must be unique")
    for row in stages:
        for dep in json.loads(row["depends_on_json"]):
            if dep not in outputs:
                raise ValueError(f"Unknown staging dependency: {dep}")
    output_set = set(outputs.values())
    metric_set = {m["code"] for m in dictionary["metrics"]}
    for product in dictionary["products"]:
        if product["parentMetric"] not in metric_set:
            raise ValueError(f"Unknown parent metric: {product['parentMetric']}")
        for stage in product["stages"]:
            if stage not in output_set:
                raise ValueError(f"Unknown product stage: {stage}")
    for term in ontology["terms"]:
        output = term["term"].split(".", 1)[0]
        if output not in output_set:
            raise ValueError(f"No staging output for term {term['term']}")
    return dictionary, ontology, stages, outputs


def run(client: Neo4j, dictionary: dict, ontology: dict, stages: list[dict], outputs: dict[str, str]):
    for label in LABELS:
        client.query(
            f"CREATE CONSTRAINT aum_{label.lower()}_key IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.key IS UNIQUE"
        )

    metric_rows = []
    for metric in dictionary["metrics"]:
        props = {k: v for k, v in metric.items() if k != "code"}
        props.update({
            "code": metric["code"],
            "ontologyId": "aum",
            "dictionaryVersion": dictionary["version"],
            "intendedGrain": dictionary["intendedGrain"],
        })
        metric_rows.append({"key": key("metric", metric["code"]), "properties": props})
    client.rows("""
        UNWIND $rows AS row
        MERGE (m:BusinessMetric {key: row.key})
        SET m += row.properties
    """, metric_rows)
    client.query("""
        MATCH (o:Ontology {key:'aum'}), (m:BusinessMetric {key:'aum:metric:aum_total_month_end'})
        MERGE (o)-[:HAS_BUSINESS_MODEL]->(m)
    """)
    client.rows("""
        UNWIND $rows AS row
        MATCH (parent:BusinessMetric {key: row.parentKey})
        MATCH (child:BusinessMetric {key: row.childKey})
        MERGE (parent)-[:HAS_COMPONENT]->(child)
    """, [
        {"parentKey": key("metric", parent), "childKey": key("metric", child)}
        for parent, child in dictionary["metricHierarchy"]
    ])

    product_rows = []
    implementation_rows = []
    for product in dictionary["products"]:
        props = {k: v for k, v in product.items() if k not in {"code", "parentMetric", "stages"}}
        props.update({"code": product["code"], "ontologyId": "aum", "dictionaryVersion": dictionary["version"]})
        product_rows.append({
            "key": key("product", product["code"]),
            "metricKey": key("metric", product["parentMetric"]),
            "properties": props,
        })
        for stage in product["stages"]:
            implementation_rows.append({
                "productKey": key("product", product["code"]),
                "stageKey": key("stage", stage),
            })
    client.rows("""
        UNWIND $rows AS row
        MATCH (m:BusinessMetric {key: row.metricKey})
        MERGE (p:ProductCategory {key: row.key})
        SET p += row.properties
        MERGE (m)-[:INCLUDES_PRODUCT]->(p)
    """, product_rows)

    stage_rows = []
    dependency_rows = []
    source_table_rows = []
    for stage in stages:
        output = stage["output_object"]
        override = dictionary.get("stageOverrides", {}).get(output, {})
        source_tables = json.loads(stage["source_tables_json"])
        props = {
            "outputObject": output,
            "stagingSqlId": stage["staging_sql_id"],
            "stageLevel": stage["stage_level"],
            "sourceTables": source_tables,
            "ontologyId": "aum",
            "dictionaryVersion": dictionary["version"],
            "name": output,
            **override,
        }
        stage_rows.append({"key": key("stage", output), "properties": props})
        for table in source_tables:
            source_table_rows.append({
                "stageKey": key("stage", output),
                "tableKey": f"aum:{table}",
                "table": table,
            })
        for dep in json.loads(stage["depends_on_json"]):
            dependency_rows.append({
                "stageKey": key("stage", output),
                "dependencyKey": key("stage", outputs[dep]),
            })
    client.rows("""
        UNWIND $rows AS row
        MERGE (s:StagingOutput {key: row.key})
        SET s += row.properties
    """, stage_rows)
    client.rows("""
        UNWIND $rows AS row
        MATCH (p:ProductCategory {key: row.productKey})
        MATCH (s:StagingOutput {key: row.stageKey})
        MERGE (p)-[:IMPLEMENTED_BY]->(s)
    """, implementation_rows)
    client.rows("""
        UNWIND $rows AS row
        MATCH (s:StagingOutput {key: row.stageKey})
        MATCH (dep:StagingOutput {key: row.dependencyKey})
        MERGE (s)-[:DEPENDS_ON]->(dep)
    """, dependency_rows)
    client.rows("""
        UNWIND $rows AS row
        MATCH (s:StagingOutput {key: row.stageKey})
        MERGE (tb:PhysicalTable {key: row.tableKey})
        SET tb.name = row.table
        MERGE (s)-[:READS_FROM]->(tb)
    """, source_table_rows)
    client.query("""
        MATCH (m:BusinessMetric {key:'aum:metric:aum_total_month_end'})
        MATCH (s:StagingOutput {key:'aum:stage:AUM'})
        MERGE (m)-[:CALCULATED_FROM]->(s)
    """)

    term_rows = [
        {
            "termKey": f"aum:{term['id']}",
            "stageKey": key("stage", term["term"].split(".", 1)[0]),
        }
        for term in ontology["terms"]
    ]
    client.rows("""
        UNWIND $rows AS row
        MATCH (s:StagingOutput {key: row.stageKey})
        MATCH (t:Term {key: row.termKey})
        MERGE (s)-[:DESCRIBED_BY]->(t)
    """, term_rows)

    rule_rows = []
    for rule in dictionary["rules"]:
        props = {k: v for k, v in rule.items() if k not in {"code", "stage", "metric"}}
        props.update({"code": rule["code"], "ontologyId": "aum"})
        rule_rows.append({
            "key": key("rule", rule["code"]),
            "stageKey": key("stage", rule["stage"]) if rule.get("stage") else None,
            "metricKey": key("metric", rule["metric"]) if rule.get("metric") else None,
            "properties": props,
        })
    client.rows("""
        UNWIND $rows AS row
        MERGE (r:CalculationRule {key: row.key})
        SET r += row.properties
    """, rule_rows)
    client.rows("""
        UNWIND $rows AS row
        MATCH (r:CalculationRule {key: row.key})
        MATCH (s:StagingOutput {key: row.stageKey})
        MERGE (s)-[:USES_CALCULATION_RULE]->(r)
    """, [row for row in rule_rows if row["stageKey"]])
    client.rows("""
        UNWIND $rows AS row
        MATCH (r:CalculationRule {key: row.key})
        MATCH (m:BusinessMetric {key: row.metricKey})
        MERGE (m)-[:USES_CALCULATION_RULE]->(r)
    """, [row for row in rule_rows if row["metricKey"]])

    dimensions = [
        ("customer", "客戶", "CUST_ID", "跨來源客戶識別碼的一致性尚待驗證"),
        ("month", "指定月份", "YYYYMMDD", "每分類取當月最新日期；不保證為曆月最後一天"),
        ("type", "資產類型", "TYP", "存款或投資"),
        ("company", "承作端", "COMP", "銀行或證券"),
        ("product", "產品", "PROD", "彙整 SQL 指定或由來源欄位帶入"),
        ("subtype", "產品子類", "TYP_SUB_DTL", "存款來源可有子分類"),
    ]
    client.rows("""
        UNWIND $rows AS row
        MATCH (m:BusinessMetric {key:'aum:metric:aum_total_month_end'})
        MERGE (d:BusinessDimension {key: row.key})
        SET d.name = row.name, d.field = row.field,
            d.note = row.note, d.ontologyId = 'aum'
        MERGE (m)-[:HAS_DIMENSION]->(d)
    """, [
        {"key": key("dimension", code), "name": name, "field": field, "note": note}
        for code, name, field, note in dimensions
    ])

    # The JSON's raw aliases remain on Term, but unreviewed values such as
    # "exchange rate" must not appear as business synonym relationships.
    client.query("""
        MATCH (t:Term {ontologyId:'aum'})-[r:HAS_ALIAS]->(:Alias)
        DELETE r
    """)
    client.query("""
        MATCH (a:Alias)
        WHERE a.key STARTS WITH 'aum:' AND NOT EXISTS { MATCH (a)--() }
        DELETE a
    """)

    checks = {
        "business metrics": (len(dictionary["metrics"]), "MATCH (n:BusinessMetric {ontologyId:$ontologyId}) RETURN count(n)"),
        "product categories": (len(dictionary["products"]), "MATCH (n:ProductCategory {ontologyId:$ontologyId}) RETURN count(n)"),
        "staging outputs": (len(stages), "MATCH (n:StagingOutput {ontologyId:$ontologyId}) RETURN count(n)"),
        "staging-to-term links": (len(term_rows), "MATCH (:StagingOutput {ontologyId:$ontologyId})-[:DESCRIBED_BY]->(:Term) RETURN count(*)"),
        "staging dependencies": (len(dependency_rows), "MATCH (:StagingOutput {ontologyId:$ontologyId})-[:DEPENDS_ON]->() RETURN count(*)"),
        "staging source-table links": (len(source_table_rows), "MATCH (:StagingOutput {ontologyId:$ontologyId})-[:READS_FROM]->() RETURN count(*)"),
        "unreviewed synonym links": (0, "MATCH (:Term {ontologyId:$ontologyId})-[:HAS_ALIAS]->() RETURN count(*)"),
    }
    for label, (expected, query) in checks.items():
        actual = client.count(query, "aum")
        if actual != expected:
            raise RuntimeError(f"{label}: expected {expected}, got {actual}")
        print(f"{label}: {actual}")
    connected_stages = client.count("""
        MATCH (:StagingOutput {key:'aum:stage:AUM'})-[:DEPENDS_ON*0..3]->(s:StagingOutput)
        RETURN count(DISTINCT s)
    """, "aum")
    if connected_stages != len(stages):
        raise RuntimeError(f"Only {connected_stages} of {len(stages)} staging outputs reach AUM")
    connected_products = client.count("""
        MATCH (:BusinessMetric {key:'aum:metric:aum_total_month_end'})
          -[:HAS_COMPONENT*0..3]->(:BusinessMetric)
          -[:INCLUDES_PRODUCT]->(p:ProductCategory)
        RETURN count(DISTINCT p)
    """, "aum")
    if connected_products != len(dictionary["products"]):
        raise RuntimeError(f"Only {connected_products} of {len(dictionary['products'])} products reach total AUM")
    print(f"Connected business graph: {connected_products} products and {connected_stages} staging outputs")
    for stage_name in ("AUM_012", "AUM_027", "AUM_028"):
        result = client.query("""
            MATCH (:BusinessMetric {key:'aum:metric:aum_total_month_end'})
              -[:HAS_COMPONENT*1..3]->(:BusinessMetric)
              -[:INCLUDES_PRODUCT]->(:ProductCategory)
              -[:IMPLEMENTED_BY]->(s:StagingOutput {key:$stageKey})
            RETURN count(DISTINCT s)
        """, {"stageKey": key("stage", stage_name)})
        count = result["data"]["values"][0][0]
        if count != 1:
            raise RuntimeError(f"Business path missing for {stage_name}")
    print("Verified AUM_012, AUM_027, and AUM_028 are reachable from total AUM")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    folder = Path(__file__).resolve().parent
    parser.add_argument("--dictionary", type=Path, default=folder / "AUM_business_dictionary.json")
    parser.add_argument("--ontology", type=Path, default=folder / "AUM Ontology.json")
    parser.add_argument("--staging", type=Path, default=folder.parent / "deliverables/staging/v0.2/AUM_Staging_SQL_KB_v0.2.csv")
    parser.add_argument("--url", default="http://127.0.0.1:7474")
    parser.add_argument("--database", default="neo4j")
    parser.add_argument("--user", default="neo4j")
    args = parser.parse_args()
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        parser.error("Set NEO4J_PASSWORD in the environment")
    dictionary, ontology, stages, outputs = load_inputs(args.dictionary, args.ontology, args.staging)
    run(Neo4j(args.url, args.database, args.user, password), dictionary, ontology, stages, outputs)


if __name__ == "__main__":
    main()
