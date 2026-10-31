"""Restore into a dedicated EMPTY local database, preserving all business properties.
Existing databases are never cleared or overwritten. Aura element IDs are only
temporary restore identities; application queries use local element IDs afterwards.
"""
import collections,hashlib,json,re
from pathlib import Path
from runtime import ROOT,STATE,rows
OUT=ROOT/'deliverables'/'local_graph'/'20261020'
FULL=ROOT/'deliverables/graph_exports/20261014/Aura_完整圖譜快照.json'
LATEST=ROOT/'deliverables/concept_update/20261018_remove_offering_type/aura.after.export.json'

def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def fingerprint(nodes,edges):
    ns=sorted((n['id'],sorted(n['labels']),n['properties']) for n in nodes)
    es=sorted((e['source'],e['type'],e['target'],json.dumps(e['properties'],sort_keys=True,ensure_ascii=False)) for e in edges)
    return digest([ns,es])

def main():
    full=json.loads(FULL.read_text(encoding='utf-8'));latest=json.loads(LATEST.read_text(encoding='utf-8'))[0]['snapshot']
    old_concept={n['id'] for n in full['nodes'] if 'PBConcept' in n['labels']}
    nodes=[n for n in full['nodes'] if n['id'] not in old_concept]+latest['nodes']
    edges=[e for e in full['relationships'] if e['source'] not in old_concept and e['target'] not in old_concept]+latest['relationships']
    keys={n['id'] for n in nodes}
    assert len(keys)==len(nodes)==1618 and len(edges)==4649
    assert all(e['source'] in keys and e['target'] in keys for e in edges)
    assert len(latest['nodes'])==41 and len(latest['relationships'])==69
    source_digest=fingerprint(nodes,edges)
    count=rows('MATCH (n) RETURN count(n)')[0][0]
    if count:
        previous=OUT/'import-verification.json'
        if previous.exists() and json.loads(previous.read_text(encoding='utf-8'))['sourceFingerprint']==source_digest:
            print('Source already restored; no writes performed.');return
        raise RuntimeError('Refusing to import into a non-empty database without a matching completed restore record.')
    for n in nodes:
        for label in n['labels']:assert re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',label),label
    for e in edges:assert re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*',e['type']),e['type']
    rows('CREATE CONSTRAINT pb_restore_identity IF NOT EXISTS FOR (n:_PBRestore) REQUIRE n._restoreId IS UNIQUE')
    groups=collections.defaultdict(list)
    for n in nodes:groups[tuple(sorted(n['labels']))].append(n)
    for labels,items in groups.items():
        label_text=':'.join(labels)
        for start in range(0,len(items),40):
            batch=items[start:start+40]
            result=rows(f'UNWIND $rows AS row CREATE (n:_PBRestore:{label_text}) SET n=row.properties SET n._restoreId=row.id RETURN count(n)',{'rows':batch})
            assert result[0][0]==len(batch)
    groups=collections.defaultdict(list)
    for e in edges:groups[e['type']].append(e)
    for typ,items in groups.items():
        for start in range(0,len(items),100):
            batch=items[start:start+100]
            result=rows(f'UNWIND $rows AS row MATCH (a:_PBRestore {{_restoreId:row.source}}),(b:_PBRestore {{_restoreId:row.target}}) CREATE (a)-[r:{typ}]->(b) SET r=row.properties RETURN count(r)',{'rows':batch})
            assert result[0][0]==len(batch)
    actual_nodes=[{'id':ident,'labels':[l for l in labels if l!='_PBRestore'],'properties':{k:v for k,v in props.items() if k!='_restoreId'}} for ident,labels,props in rows('MATCH (n:_PBRestore) RETURN n._restoreId,labels(n),properties(n)')]
    actual_edges=[{'source':a,'type':t,'target':b,'properties':props} for a,t,b,props in rows('MATCH (a:_PBRestore)-[r]->(b:_PBRestore) RETURN a._restoreId,type(r),b._restoreId,properties(r)')]
    actual_digest=fingerprint(actual_nodes,actual_edges)
    assert actual_digest==source_digest,'Restore content differs from source.'
    rows('MATCH (n:_PBRestore) REMOVE n:_PBRestore,n._restoreId RETURN count(n)')
    rows('DROP CONSTRAINT pb_restore_identity IF EXISTS')
    counts={'nodes':rows('MATCH (n) RETURN count(n)')[0][0],'relationships':rows('MATCH ()-[r]->() RETURN count(r)')[0][0],'conceptNodes':rows('MATCH (n:PBConcept) RETURN count(n)')[0][0],'conceptRelationships':rows('MATCH (:PBConcept)-[r]->(:PBConcept) RETURN count(r)')[0][0]}
    assert counts=={'nodes':1618,'relationships':4649,'conceptNodes':41,'conceptRelationships':69}
    OUT.mkdir(parents=True,exist_ok=True)
    out={'status':'passed','date':'2026-10-20','sourceFingerprint':source_digest,'restoredFingerprint':actual_digest,'allLabelsPropertiesAndEndpointsPreserved':True,'counts':counts,'mappingNodes':1577,'mappingRelationships':4580,'conceptSource':str(LATEST.relative_to(ROOT)),'mappingSource':str(FULL.relative_to(ROOT)),'originalAuraElementIdsNotUsedAsLocalIds':True,'existingNeo4jCommunityContainerUntouched':True}
    (OUT/'import-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__':main()
