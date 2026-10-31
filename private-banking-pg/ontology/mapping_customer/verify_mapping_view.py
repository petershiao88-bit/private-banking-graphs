"""Read-only equivalence check against the user's exact baseline graph view."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from import_customer_mapping import HERE, KEY, Neo4j, credentials, selected_aura, ensure, protected_snapshot, digest


def elements(values):
    nodes, edges = {}, {}
    def visit(value):
        if isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            if 'elementId' in value and 'labels' in value:
                nodes[value['elementId']] = value
            elif 'elementId' in value and 'type' in value and 'startNodeElementId' in value:
                edges[value['elementId']] = value
    visit(values)
    return nodes, edges


def verify(db):
    protected_before = protected_snapshot(db)
    baseline = db.query((HERE / 'view_mapping_baseline.cypher').read_text(encoding='utf-8'))['data']
    updated = db.query((HERE / 'view_mapping_with_customer.cypher').read_text(encoding='utf-8'))['data']
    original_rows = Counter(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in baseline['values'])
    updated_rows = Counter(json.dumps(row[:4], ensure_ascii=False, sort_keys=True) for row in updated['values'])
    ensure(original_rows == updated_rows, 'Original four paths or row multiplicities changed')
    old_nodes, old_edges = elements(baseline['values'])
    same_nodes, same_edges = elements([row[:4] for row in updated['values']])
    ensure(old_nodes == same_nodes and old_edges == same_edges, 'Original graph elements changed')
    new_nodes, new_edges = elements(updated['values'])
    added_nodes = {key: value for key, value in new_nodes.items() if key not in old_nodes}
    added_edges = {key: value for key, value in new_edges.items() if key not in old_edges}
    ensure(len(added_nodes) == 1, 'Unexpected extra nodes')
    customer = next(iter(added_nodes.values()))
    ensure(customer['properties']['key'] == KEY and set(customer['labels']) == {'MappingCustomer', 'BusinessDimension'}, 'Unexpected extra Customer')
    ensure(len(added_edges) == 12 and all(edge['type'] == 'MEASURES_CUSTOMER' and
           edge['startNodeElementId'] in old_nodes and edge['endNodeElementId'] == customer['elementId']
           for edge in added_edges.values()), 'Unexpected additional relationships')
    ensure(all(not any(label in node['labels'] for label in ('Ontology', 'Term', 'SourceProperty', 'PBConcept'))
               for node in added_nodes.values()), 'Ontology/term/concept nodes added to view')
    source_path_rows = [row[3] for row in baseline['values']]
    ensure(Counter(json.dumps(path, sort_keys=True) for path in source_path_rows) ==
           Counter(json.dumps(row[3], sort_keys=True) for row in updated['values']), 'SQL lineage paths changed')
    protected_after = protected_snapshot(db)
    ensure(protected_before == protected_after, 'Read-only verification changed graph')
    report = dict(verifiedAt=datetime.now(timezone.utc).isoformat(),
                  baselineRows=len(baseline['values']), updatedRows=len(updated['values']),
                  baselineGraphNodes=len(old_nodes), baselineGraphRelationships=len(old_edges),
                  updatedGraphNodes=len(new_nodes), updatedGraphRelationships=len(new_edges),
                  addedNodes=1, addedRelationships=12, originalFourPathsExactlyPreserved=True,
                  originalGraphElementsExactlyPreserved=True, sqlLineagePathsExactlyPreserved=True,
                  additionalOntologyNodes=0, databaseUnchanged=True, protected=protected_before,
                  baselineGraphSha256=digest([old_nodes, old_edges]))
    (HERE / 'view_validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--credentials', type=Path, required=True)
    args = parser.parse_args()
    creds = credentials(args.credentials)
    base = selected_aura(creds['NEO4J_URI'])
    ensure(base == 'https://4bb479b2.databases.neo4j.io', 'Unexpected Aura target')
    db = Neo4j(base, 'neo4j', creds['NEO4J_USERNAME'], creds['NEO4J_PASSWORD'])
    print(json.dumps(verify(db), ensure_ascii=False))


if __name__ == '__main__':
    main()
