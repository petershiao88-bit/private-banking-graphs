"""Read metadata only; never modify the graph or query customer records."""
import argparse
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from import_aura_snapshot import credentials, selected_aura
from import_ontology_neo4j import Neo4j

HERE = Path(__file__).resolve().parent
def rows(db, query):
    result = db.query(query)
    return [dict(zip(result['data']['fields'], row)) for row in result['data']['values']]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--credentials', type=Path, required=True)
    args = parser.parse_args()
    config = credentials(args.credentials)
    db = Neo4j(selected_aura(config['NEO4J_URI']), 'neo4j', config['NEO4J_USERNAME'], config['NEO4J_PASSWORD'])
    labels = rows(db, 'MATCH (n) UNWIND labels(n) AS label RETURN label,count(*) AS count ORDER BY label')
    fields = rows(db, """MATCH (n)
     WHERE (n:PhysicalColumn OR n:SourceProperty OR n:PropertyReference OR n:BusinessConcept OR n:BusinessDimension OR n:ObjectTypeReference OR n:PBConcept)
      AND any(value IN [n.name,n.columnName,n.physicalName,n.code,n.definition]
       WHERE value IS NOT NULL AND any(term IN ['cust_id','cust id','customer','客戶','idno','wkb02'] WHERE toLower(toString(value)) CONTAINS term))
     OPTIONAL MATCH (a)-[r]->(n)
     RETURN n.key AS key,labels(n) AS labels,n.name AS name,n.columnName AS columnName,n.physicalName AS physicalName,
      n.definition AS definition,collect(DISTINCT {from:a.key,type:type(r),name:a.name}) AS incoming
     ORDER BY key LIMIT 100""")
    source_sql = rows(db, """MATCH (n:SqlStatement)
     WHERE toLower(coalesce(n.sql,'')) CONTAINS 'cust_id'
     RETURN n.key AS key,n.file AS file,n.lineStart AS lineStart,n.status AS status,n.sql AS sql ORDER BY key""")
    statements = []
    for row in source_sql:
        sql = row.pop('sql')
        matches = [sql[max(0, match.start()-45):min(len(sql), match.end()+35)].replace('\n',' ') for match in re.finditer('cust_id', sql, re.I)]
        statements.append({**row, 'customerKeyExcerpts': matches[:5]})
    explicit = rows(db, """MATCH (n)
     WHERE n:PBConcept OR n:SharedProduct OR n:BusinessMetric OR n:StagingOutput OR n:SqlTable
     WITH n,[key IN keys(n) WHERE toLower(key) CONTAINS 'customer' OR toLower(key) CONTAINS 'custid' OR toLower(key) CONTAINS 'cust_id'] AS customerProperties
     WHERE size(customerProperties)>0
     RETURN n.key AS key,labels(n) AS labels,customerProperties ORDER BY key""")
    dimensions = rows(db, """MATCH (n:BusinessDimension)
     OPTIONAL MATCH (n)-[r]-(m)
     RETURN n.key AS key,n.name AS name,n.definition AS definition,
      collect(DISTINCT {key:m.key,name:m.name,type:type(r)}) AS neighbors ORDER BY key""")
    result = {'readOnly': True, 'graphModified': False, 'labels': labels, 'customerMetadataNodes': fields,'businessDimensions':dimensions,
              'customerSqlStatements': statements, 'explicitCustomerProperties': explicit}
    (HERE/'single_jev.customer_identity_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'labels': labels,'metadataMatches':len(fields),'sqlStatementsWithCustId':len(statements),
      'explicitCustomerProperties':len(explicit),'businessDimensions':dimensions,'sampleMetadata':fields[:2],
      'sampleSql':[row for row in statements if row['lineStart']==366 and 'AUM_DETAIL' in row['file']]},ensure_ascii=False))

if __name__ == '__main__':
    main()
