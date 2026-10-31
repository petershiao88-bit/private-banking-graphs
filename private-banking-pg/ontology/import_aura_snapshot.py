"""Merge the exported graph into the user-selected Aura instance over HTTPS."""
import argparse,json,re
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse
from export_aura_graph import digest,HERE
from import_ontology_neo4j import Neo4j

MARKER='_aumIncomeTransferId'


def credentials(path):
    result={}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line:continue
        name,value=line.split('=',1);name=name.strip().removeprefix('export ').strip();value=value.strip()
        if len(value)>1 and value[0]==value[-1] and value[0] in ('\"',"'"):value=value[1:-1]
        result[name]=value
    assert result.get('NEO4J_USERNAME') and result.get('NEO4J_PASSWORD'),'Credentials file lacks username/password'
    return result


def selected_aura(uri):
    parsed=urlparse(uri)
    assert parsed.scheme in ('neo4j+s','bolt+s','https'),'A TLS Aura URI is required'
    assert parsed.hostname and parsed.hostname.endswith('.databases.neo4j.io'),'Expected an Aura instance hostname'
    assert not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
    assert parsed.path in ('','/')
    return 'https://'+parsed.hostname


def values(db,query,params=None):return db.query(query,params)['data']['values']


def verify_source(snapshot):
    assert snapshot['manifest']['format']=='aum_income_aura_snapshot_v1'
    assert digest({'nodes':snapshot['nodes'],'relationships':snapshot['relationships']})==snapshot['manifest']['contentSha256']
    keys={n['key'] for n in snapshot['nodes']}
    assert len(keys)==len(snapshot['nodes'])
    assert not any('SqlOperation' in n['labels'] for n in snapshot['nodes'])
    for node in snapshot['nodes']:
        assert node['labels'] and all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',s) for s in node['labels'])
        assert node['properties']['key']==node['key']
    for edge in snapshot['relationships']:
        assert edge['from'] in keys and edge['to'] in keys
        assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',edge['type'])
        assert MARKER not in edge['properties']
    return sorted(keys)


def check_target(db,snapshot,keys):
    expected={n['key']:n for n in snapshot['nodes']}
    existing=values(db,'MATCH (n) WHERE n.key IN $keys RETURN n.key,labels(n),properties(n)',{'keys':keys})
    assert len({row[0] for row in existing})==len(existing),'Duplicate target keys'
    for key,labels,props in existing:
        assert sorted(labels)==expected[key]['labels'] and props==expected[key]['properties'],'Target key collision: '+key
    foreign=values(db,f'''MATCH (a)-[r]->(b) WHERE a.key IN $keys AND b.key IN $keys
      AND r.{MARKER} IS NULL RETURN count(r)''',{'keys':keys})[0][0]
    assert foreign==0,'Target has existing relationships in this namespace; use a fresh instance or review the collision'
    totals=values(db,'MATCH (n) RETURN count(n)')[0][0],values(db,'MATCH ()-[r]->() RETURN count(r)')[0][0]
    return {'existingMatchingNodes':len(existing),'targetNodesBefore':totals[0],'targetRelationshipsBefore':totals[1]}


def protected(db,keys):
    nodes=values(db,'MATCH (n) WHERE NOT coalesce(n.key,\'\') IN $keys RETURN elementId(n),labels(n),properties(n) ORDER BY elementId(n)',{'keys':keys})
    edges=values(db,f'MATCH (a)-[r]->(b) WHERE r.{MARKER} IS NULL RETURN elementId(a),type(r),elementId(b),properties(r) ORDER BY elementId(a),type(r),elementId(b)')
    return digest([nodes,edges])


def merge(db,snapshot):
    groups=defaultdict(list)
    for node in snapshot['nodes']:groups[tuple(node['labels'])].append(node)
    for labels,nodes in groups.items():
        primary=labels[0]
        db.query(f'CREATE CONSTRAINT aura_transfer_{primary.lower()}_key IF NOT EXISTS FOR (n:{primary}) REQUIRE n.key IS UNIQUE')
        label_sql=':'.join(labels)
        db.rows(f'UNWIND $rows AS row MERGE (n:{primary} {{key:row.key}}) SET n:{label_sql} SET n += row.properties',nodes,batch_size=50)
    edges=defaultdict(list)
    for edge in snapshot['relationships']:edges[edge['type']].append(edge)
    for kind,group in edges.items():
        db.rows(f'''UNWIND $rows AS row MATCH (a {{key:row.from}}),(b {{key:row.to}})
          MERGE (a)-[r:{kind} {{{MARKER}:row.migrationId}}]->(b) SET r += row.properties''',group,batch_size=50)


def verify_target(db,snapshot,keys):
    actual=values(db,'MATCH (n) WHERE n.key IN $keys RETURN n.key,labels(n),properties(n) ORDER BY n.key',{'keys':keys})
    expected_nodes={n['key']:(n['labels'],n['properties']) for n in snapshot['nodes']}
    actual_nodes={key:(sorted(labels),props) for key,labels,props in actual}
    assert len(actual)==len(expected_nodes) and actual_nodes==expected_nodes,'Node labels/properties differ'
    actual_edges=values(db,f'MATCH (a)-[r]->(b) WHERE r.{MARKER} IS NOT NULL RETURN a.key,type(r),b.key,properties(r)')
    mapped={}
    for source,kind,target,props in actual_edges:
        mid=props.pop(MARKER)
        assert mid not in mapped,'Duplicate imported edge'
        mapped[mid]=(source,kind,target,props)
    expected_edges={e['migrationId']:(e['from'],e['type'],e['to'],e['properties']) for e in snapshot['relationships']}
    assert mapped==expected_edges,'Relationship properties/direction differ'
    for target,count,file in [('INCOME_TMP01',24,'sources/sql/9.INCOME_SMY.sql'),('AUM',13,'sources/sql/2._AUM_SUMY.sql')]:
        assert values(db,'MATCH (:SqlTable)-[r:UNION]->(:SqlTable {name:$name}) WHERE r.file=$file AND r.status=\'active_sql\' RETURN count(r)',{'name':target,'file':file})==[[count]]
    for side,kind,root in [('aum','MEASURED_BY_AUM|AUM_ROLLS_UP_TO','aum:metric:aum_total_month_end'),('income','MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING|INCOME_ROLLS_UP_TO','income:metric:income_total_customer_month')]:
        assert values(db,f'MATCH (p:SharedProduct {{ontologyId:\'pb_shared\'}}) WHERE NOT (p)-[:{kind}*1..5]->(:BusinessMetric {{key:$key}}) RETURN count(p)',{'key':root})==[[0]]
    return {'nodes':len(actual),'relationships':len(actual_edges),'allLabelsPropertiesAndDirectionsMatch':True,'incomeUnionBranches':24,'aumUnionBranches':13,'allSharedProductsReachBothBusinessRoots':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--credentials',type=Path,required=True)
    parser.add_argument('--uri')
    parser.add_argument('--database')
    parser.add_argument('--snapshot',type=Path,default=HERE/'aura_migration/graph_snapshot.json')
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    creds=credentials(args.credentials)
    uri=args.uri or creds.get('NEO4J_URI')
    assert uri,'Missing Aura URI'
    base=selected_aura(uri)
    if args.uri and creds.get('NEO4J_URI'):assert selected_aura(creds['NEO4J_URI'])==base,'URI and credentials file refer to different instances'
    database=args.database or creds.get('NEO4J_DATABASE','neo4j')
    assert re.fullmatch(r'[A-Za-z0-9_.-]+',database)
    snapshot=json.loads(args.snapshot.read_text(encoding='utf-8'))
    keys=verify_source(snapshot)
    db=Neo4j(base,database,creds['NEO4J_USERNAME'],creds['NEO4J_PASSWORD'])
    report=check_target(db,snapshot,keys)
    if args.check_only:
        print(json.dumps({'checkOnly':'passed','nodesToImport':len(keys),'relationshipsToImport':len(snapshot['relationships']),**report},ensure_ascii=False));return
    before=protected(db,keys)
    merge(db,snapshot)
    first=verify_target(db,snapshot,keys)
    assert protected(db,keys)==before,'Unrelated target data changed'
    merge(db,snapshot)
    second=verify_target(db,snapshot,keys)
    assert first==second and protected(db,keys)==before,'Idempotence or target preservation failed'
    report.update(importValidation=second,idempotentRerun=True,unrelatedTargetDataPreserved=True,
                  sourceContentSha256=snapshot['manifest']['contentSha256'],auraHost=urlparse(base).hostname,database=database)
    (HERE/'aura_migration/import_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'import':'passed',**second,'idempotentRerun':True},ensure_ascii=False))


if __name__=='__main__':main()
