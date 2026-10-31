"""Merge SQL lineage without replacing business nodes or existing relationships."""
import argparse
from collections import Counter,defaultdict
import hashlib,json,os,re
from pathlib import Path
from import_ontology_neo4j import Neo4j
from verify_sql_lineage_plan import verify
from sql_table_links import LINK_TYPES

FOLDER=Path(__file__).resolve().parent
OWNER='sql_lineage_v1'
NS='sql_lineage'
LABELS={'SqlLineageRoot','SqlSourceFile','SqlStatement','SqlTable'}
TYPES={'HAS_SQL_FILE','HAS_STATEMENT','TARGETS_TABLE','READS_TABLE','NEXT_STATEMENT'}|LINK_TYPES


def rows(db,q,params=None):
    return db.query(q,params)['data']['values']


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def protected_snapshot(db):
    nodes=rows(db,"MATCH (n) WHERE coalesce(n.origin,'') <> $owner RETURN n.key,labels(n) ORDER BY n.key",{'owner':OWNER})
    rels=rows(db,"MATCH (a)-[r]->(b) WHERE coalesce(r.origin,'') <> $owner RETURN a.key,type(r),b.key,properties(r) ORDER BY a.key,type(r),b.key",{'owner':OWNER})
    business=rows(db,"MATCH (n) WHERE n:BusinessMetric OR n:ProductCategory RETURN n.key,properties(n),labels(n) ORDER BY n.key")
    return {'nodeCount':len(nodes),'relationshipCount':len(rels),'nodesSha256':digest(nodes),
            'relationshipsSha256':digest(rels),'businessNodesSha256':digest(business)}


def validate_flat(props):
    assert isinstance(props,dict)
    for k,v in props.items():
        assert isinstance(k,str)
        assert isinstance(v,(str,bool,int,float,list)),(k,type(v))
        if isinstance(v,list):
            assert all(isinstance(x,(str,bool,int,float)) for x in v),(k,v)
            assert len(set(type(x) for x in v))<=1,(k,v)


def check(db,plan):
    report=verify(plan)
    keys={n['key'] for n in plan['nodes']}
    assert len(keys)==len(plan['nodes'])
    for n in plan['nodes']:
        assert n['label'] in LABELS and n['key'].startswith(NS+':')
        validate_flat(n['properties'])
    for e in plan['relationships']:
        assert e['type'] in TYPES and e['from'] in keys and e['to'] in keys
        validate_flat(e['properties'])
    collisions=rows(db,"MATCH (n) WHERE n.key IN $keys AND coalesce(n.origin,'') <> $owner RETURN n.key",{'keys':sorted(keys),'owner':OWNER})
    assert not collisions,collisions
    existing_stages=rows(db,'MATCH (s:StagingOutput) RETURN s.key,s.outputObject,s.ontologyId')
    table_names={n['properties']['name'] for n in plan['nodes'] if n['label']=='SqlTable'}
    missing=[k for k,name,domain in existing_stages if str(name).upper() not in table_names]
    assert not missing,missing
    report.update(planLabels=dict(Counter(n['label'] for n in plan['nodes'])),
                  planRelationships=len(plan['relationships']),stageBridgeCandidates=len(existing_stages))
    return report


def merge(db,plan):
    for label in sorted(LABELS):
        db.query(f'CREATE CONSTRAINT sql_lineage_{label.lower()}_key IF NOT EXISTS FOR (n:{label}) REQUIRE n.key IS UNIQUE')
    for label in sorted(LABELS):
        db.rows(f'UNWIND $rows AS row MERGE (n:{label} {{key:row.key}}) SET n += row.properties',
                [n for n in plan['nodes'] if n['label']==label])
    for kind in sorted(TYPES):
        db.rows(f'''UNWIND $rows AS row
          MATCH (a {{key:row.from}}), (b {{key:row.to}})
          MERGE (a)-[r:{kind} {{lineageEdgeId:row.properties.lineageEdgeId}}]->(b)
          SET r += row.properties''',[e for e in plan['relationships'] if e['type']==kind])
    db.query('''MATCH (s:StagingOutput), (t:SqlTable)
      WHERE t.key=$prefix+toUpper(s.outputObject)
      MERGE (s)-[r:REPRESENTS_SQL_TABLE {origin:$owner}]->(t)
      SET r.ontologyId=$ns, s.sqlDefinitionStatus=t.definitionStatus,
          s.sqlLineageVersion=$owner''',{'prefix':NS+':table:','owner':OWNER,'ns':NS})
    db.query('''MATCH (p:PhysicalTable), (t:SqlTable)
      WHERE t.physicalName=toUpper(coalesce(p.physicalTable,p.name))
      MERGE (p)-[r:REPRESENTS_SQL_TABLE {origin:$owner}]->(t)
      SET r.ontologyId=$ns''',{'owner':OWNER,'ns':NS})
    db.query('''MATCH (stage:StagingOutput)-[:REPRESENTS_SQL_TABLE]->(table:SqlTable)
      MATCH (statement:SqlStatement)-[:TARGETS_TABLE]->(table)
      WHERE statement.domain=stage.ontologyId
      MERGE (stage)-[r:SUPPORTED_BY_SQL {origin:$owner}]->(statement)
      SET r.ontologyId=$ns''',{'owner':OWNER,'ns':NS})
    # Connect both old SqlEvidence ID stubs and existing statement evidence.
    db.query('''MATCH (s:StagingOutput)-[:DESCRIBED_BY]->(:Term)-[:SUPPORTED_BY_SQL]->(e:SqlEvidence)
      MATCH (s)-[bridge:SUPPORTED_BY_SQL]->(statement:SqlStatement)
      WHERE bridge.origin=$owner
        AND (e.file IS NULL OR (e.file=statement.file AND e.lineStart=statement.lineStart)
             OR (e.status='commented_out_sql' AND statement.status='commented_out_sql'))
      MERGE (e)-[r:REPRESENTS_SQL_STATEMENT {origin:$owner}]->(statement)
      SET r.ontologyId=$ns''',{'owner':OWNER,'ns':NS})
    aliases={'aum:aum_detail.sql':'1.AUM_DETAIL.sql','aum:aum_rollup.sql':'2._AUM_SUMY.sql'}
    mappings=[{'old':k,'new':NS+':file:'+v} for k,v in aliases.items()]
    # Parameters are passed explicitly; no source filenames or secrets enter code.
    db.query('''UNWIND $mappings AS row MATCH (d:SourceDocument {key:row.old}), (f:SqlSourceFile {key:row.new})
      MERGE (d)-[r:PRESERVED_AS_SQL_FILE {origin:$owner}]->(f) SET r.ontologyId=$ns''',
             {'mappings':mappings,'owner':OWNER,'ns':NS})
    db.query('''MATCH (d:SourceDocument), (f:SqlSourceFile)
      WHERE coalesce(d.path,d.location)=f.path
      MERGE (d)-[r:PRESERVED_AS_SQL_FILE {origin:$owner}]->(f) SET r.ontologyId=$ns''',
             {'owner':OWNER,'ns':NS})


def inspect(db,plan):
    report={}
    report['nodeCounts']=rows(db,'MATCH (n {origin:$owner}) RETURN labels(n),count(*) ORDER BY labels(n)',{'owner':OWNER})
    report['ownedRelationships']=rows(db,'MATCH ()-[r {origin:$owner}]->() RETURN count(r)',{'owner':OWNER})[0][0]
    for label in LABELS:
        expected=sum(n['label']==label for n in plan['nodes'])
        actual=rows(db,f'MATCH (n:{label} {{origin:$owner}}) RETURN count(n)',{'owner':OWNER})[0][0]
        assert actual==expected,(label,expected,actual)
    actual_plan_edges=rows(db,'MATCH ()-[r {origin:$owner}]->() WHERE r.lineageEdgeId IS NOT NULL RETURN count(r)',{'owner':OWNER})[0][0]
    assert actual_plan_edges==len(plan['relationships'])
    report['stageBridges']=rows(db,'MATCH (:StagingOutput)-[r:REPRESENTS_SQL_TABLE {origin:$owner}]->(:SqlTable) RETURN count(r)',{'owner':OWNER})[0][0]
    assert report['stageBridges']==86
    report['missingStageBridges']=rows(db,"MATCH (s:StagingOutput) WHERE NOT (s)-[:REPRESENTS_SQL_TABLE]->(:SqlTable) RETURN count(s)")[0][0]
    assert report['missingStageBridges']==0
    report['operationNodes']=rows(db,'MATCH (n:SqlOperation {origin:$owner,ontologyId:$ns}) RETURN count(n)',{'owner':OWNER,'ns':NS})[0][0]
    assert report['operationNodes']==0
    for output,file,branches in [('INCOME_TMP01','sources/sql/9.INCOME_SMY.sql',24),('AUM','sources/sql/2._AUM_SUMY.sql',13)]:
        actual=rows(db,'''MATCH (:SqlTable)-[r:UNION]->(:SqlTable {name:$output})
          WHERE r.file=$file AND r.status='active_sql'
          RETURN r.unionBranchOrders[0],r.unionDeduplication ORDER BY r.unionBranchOrders[0]''',{'output':output,'file':file})
        assert actual==[[i,['exact_projected_rows']] for i in range(1,branches+1)],actual
        report[output+'UnionBranches']=len(actual)
    duplicate=rows(db,'''MATCH (a)-[r {origin:$owner}]->(b)
      WITH a,type(r) AS kind,b,coalesce(r.lineageEdgeId,'bridge') AS id,count(*) AS c
      WHERE c>1 RETURN count(*)''',{'owner':OWNER})[0][0]
    assert duplicate==0,duplicate
    report['duplicateOwnedRelationships']=duplicate
    cases=[('sql_lineage:table:DSINS.INSU_RPT_Q01','sql_lineage:table:INCOME_TMP01'),
           ('sql_lineage:table:DSDEP.DEP_NT_ACCT','sql_lineage:table:AUM')]
    report['representativePaths']=[]
    for start,target in cases:
        result=rows(db,'''MATCH p=shortestPath((src:SqlTable {key:$source})-[:TRANSFORMS_TO|UNION|UNION_ALL|LEFT_JOIN|INNER_JOIN|JOIN|CROSS_JOIN|INSERT_FROM*1..15]->(dst:SqlTable {key:$target}))
          WHERE all(r IN relationships(p) WHERE r.status='active_sql')
          RETURN length(p),[n IN nodes(p) | n.name]''',{'source':start,'target':target})
        assert result,(start,target)
        report['representativePaths'].append(result[0])
    report['statusCounts']=rows(db,'MATCH (s:SqlStatement) RETURN s.status,count(*) ORDER BY s.status')
    return report


def remove_previous_operation_model(db,plan):
    # Only the operation nodes introduced by this importer are eligible.
    foreign=rows(db,'''MATCH (n:SqlOperation {origin:$owner,ontologyId:$ns})-[r]-()
      WHERE coalesce(r.origin,'')<>$owner OR coalesce(r.ontologyId,'')<>$ns
      RETURN count(r)''',{'owner':OWNER,'ns':NS})[0][0]
    assert foreign==0,'An operation node has unrelated relationships; refusing removal'
    count=rows(db,'MATCH (n:SqlOperation {origin:$owner,ontologyId:$ns}) RETURN count(n)',{'owner':OWNER,'ns':NS})[0][0]
    db.query('MATCH (n:SqlOperation {origin:$owner,ontologyId:$ns}) DETACH DELETE n',{'owner':OWNER,'ns':NS})
    db.query('''MATCH ()-[r {origin:$owner,ontologyId:$ns}]->()
      WHERE r.lineageEdgeId IS NOT NULL AND NOT r.lineageEdgeId IN $ids DELETE r''',
      {'owner':OWNER,'ns':NS,'ids':[e['properties']['lineageEdgeId'] for e in plan['relationships']]})
    return count


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--plan',type=Path,default=FOLDER/'SQL_lineage_graph_plan.json')
    args=parser.parse_args()
    password=os.environ.get('NEO4J_PASSWORD')
    if not password:parser.error('Set NEO4J_PASSWORD in the environment')
    db=Neo4j('http://127.0.0.1:7474','neo4j','neo4j',password)
    plan=json.loads(args.plan.read_text(encoding='utf-8'))
    report=check(db,plan)
    before=protected_snapshot(db)
    report['protectedBefore']=before
    if args.check_only:
        print(json.dumps({'checkOnly':'passed','stageBridgeCandidates':report['stageBridgeCandidates'],
                          'nodes':len(plan['nodes']),'relationships':len(plan['relationships'])},ensure_ascii=False))
        return
    merge(db,plan)
    report['removedPreviousOperationNodes']=remove_previous_operation_model(db,plan)
    first=inspect(db,plan)
    assert protected_snapshot(db)==before,'Existing business graph or relationships changed'
    # Repeat exactly the same merge and verify that nothing duplicates.
    merge(db,plan)
    second=inspect(db,plan)
    assert first==second,'SQL lineage import is not idempotent'
    after=protected_snapshot(db)
    assert after==before
    report.update(importValidation=second,protectedAfter=after,originalGraphPreserved=True,idempotentRerun=True)
    (FOLDER/'SQL_lineage_graph_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'import':'passed','originalGraphPreserved':True,'idempotentRerun':True,**second},ensure_ascii=False))


if __name__=='__main__':main()
