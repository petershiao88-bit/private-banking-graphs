"""Export the existing AUM/Income graph, including SQL evidence, without writes."""
import hashlib,json,os,re,shutil,zipfile
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from import_ontology_neo4j import Neo4j

HERE=Path(__file__).resolve().parent
SCOPE=['aum','income','pb_shared','sql_lineage']


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')).hexdigest()


def export():
    password=os.environ.get('NEO4J_PASSWORD')
    if not password:raise RuntimeError('Set local NEO4J_PASSWORD')
    db=Neo4j('http://127.0.0.1:7474','neo4j','neo4j',password)
    query='''MATCH (n) WHERE n.ontologyId IN $scope
      OR any(ns IN $scope WHERE n.key=ns OR n.key STARTS WITH ns+':')
      RETURN n.key,labels(n),properties(n) ORDER BY n.key'''
    data=db.query(query,{'scope':SCOPE})['data']['values']
    nodes=[{'key':key,'labels':sorted(labels),'properties':props} for key,labels,props in data]
    keys=[n['key'] for n in nodes]
    assert all(isinstance(k,str) and k for k in keys)
    assert len(set(keys))==len(keys),'Duplicate source keys'
    assert not any('SqlOperation' in n['labels'] for n in nodes)
    for n in nodes:
        assert n['properties']['key']==n['key']
        assert all(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',label) for label in n['labels'])
    external=db.query('''MATCH (a)-[r]-(b) WHERE a.key IN $keys AND NOT coalesce(b.key,'') IN $keys
      RETURN count(DISTINCT r)''',{'keys':keys})['data']['values'][0][0]
    assert external==0,('Scope would lose links to outside nodes',external)
    rows=db.query('''MATCH (a)-[r]->(b) WHERE a.key IN $keys AND b.key IN $keys
      RETURN a.key,type(r),b.key,properties(r) ORDER BY a.key,type(r),b.key''',{'keys':keys})['data']['values']
    rows.sort(key=lambda row:json.dumps(row,sort_keys=True,ensure_ascii=False))
    relationships=[];occurrences=Counter()
    for source,kind,target,props in rows:
        assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',kind)
        identity=[source,kind,target,props];signature=digest(identity)
        occurrences[signature]+=1
        relationships.append({'from':source,'type':kind,'to':target,'properties':props,
                              'migrationId':digest([identity,occurrences[signature]])})
    assert len({r['migrationId'] for r in relationships})==len(relationships)
    content={'nodes':nodes,'relationships':relationships}
    manifest={'format':'aum_income_aura_snapshot_v1','exportedAt':datetime.now(timezone.utc).isoformat(),
              'scope':SCOPE,'nodeCount':len(nodes),'relationshipCount':len(relationships),
              'namespaceCounts':dict(Counter(n['properties'].get('ontologyId',n['key'].split(':')[0]) for n in nodes)),
              'labelCounts':dict(Counter(label for n in nodes for label in n['labels'])),
              'relationshipTypes':dict(Counter(r['type'] for r in relationships)),
              'operationNodes':0,'contentSha256':digest(content),
              'fullSqlSourceFiles':sum('SqlSourceFile' in n['labels'] for n in nodes),
              'sqlStatements':sum('SqlStatement' in n['labels'] for n in nodes),
              'credentialsIncluded':False}
    snapshot=dict(manifest=manifest,**content)
    folder=HERE/'aura_migration';folder.mkdir(exist_ok=True)
    (folder/'graph_snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name in ['Shared_AUM_Income_SQL_queries.cypher','AUM_Income_Shared_browser_queries.cypher',
                 'SQL_lineage_browser_queries.cypher','SQL_lineage_README.txt']:
        shutil.copyfile(HERE/name,folder/name)
    with zipfile.ZipFile(HERE/'AUM_Income_Aura_migration.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.iterdir()):
            if path.is_file():archive.write(path,arcname=path.name)
    print(json.dumps({'export':'passed','nodes':len(nodes),'relationships':len(relationships),
                      'fullSqlSourceFiles':manifest['fullSqlSourceFiles'],'sqlStatements':manifest['sqlStatements'],
                      'operationNodes':0,'contentSha256':manifest['contentSha256']},ensure_ascii=False))


if __name__=='__main__':export()
