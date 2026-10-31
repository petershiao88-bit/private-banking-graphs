"""Keep tables as nodes and encode SQL rules on direct table relationships."""
from collections import defaultdict
import hashlib
import json

FLOW={'FLOWS_TO','UNION_INPUT','SUBQUERY_INPUT','WRITES_TO'}
LINK_TYPES={'TRANSFORMS_TO','UNION','UNION_ALL','LEFT_JOIN','INNER_JOIN',
            'RIGHT_JOIN','FULL_JOIN','CROSS_JOIN','JOIN','INSERT_FROM',
            'DELETE_ROWS','TRUNCATE_ROWS'}


def collapse(plan):
    nodes={n['key']:n for n in plan['nodes']}
    outgoing=defaultdict(list)
    rules=defaultdict(list)
    for e in plan['relationships']:
        if e['type'] in FLOW:outgoing[e['from']].append(e)
        if e['type']=='USES_RULE':rules[e['from']].append(nodes[e['to']])
    links=[]
    def add(source,target,path,operations,mutation=None):
        statement=nodes[operations[-1]['properties']['statementKey']]['properties']
        steps=[]
        for op in operations:
            steps.append(dict(op['properties']))
            steps.extend(dict(r['properties']) for r in rules[op['key']])
        kinds=[s['operationType'] for s in steps]
        union_steps=[s for s in steps if s['operationType'] in ('UNION','UNION ALL')]
        join_steps=[s for s in steps if s['operationType'].endswith('JOIN')]
        if mutation:kind=mutation
        elif union_steps:kind=union_steps[-1]['operationType'].replace(' ','_')
        elif join_steps:kind=join_steps[-1]['operationType'].replace(' ','_')
        elif 'INSERT' in kinds:kind='INSERT_FROM'
        else:kind='TRANSFORMS_TO'
        assert kind in LINK_TYPES,kind
        props={k:statement[k] for k in ['file','domain','lineStart','lineEnd','status','sourceRole','sql']}
        props.update(ontologyId='sql_lineage',origin='sql_lineage_v1',
                     statementKey=operations[-1]['properties']['statementKey'],
                     operationTypes=kinds,sqlTextKind='original_statement_slice',
                     ruleSteps=json.dumps(steps,ensure_ascii=False),
                     inputSteps=json.dumps([{'type':e['type'],**e['properties']} for e in path],ensure_ascii=False),
                     unionBranchOrders=[e['properties']['inputOrder'] for e in path if e['type']=='UNION_INPUT'],
                     unionBranchCounts=[s['branchCount'] for s in union_steps],
                     unionDeduplication=[s['deduplication'] for s in union_steps],
                     joinTypes=[s['operationType'] for s in join_steps],
                     joinConditions=[s['condition'] for s in join_steps],
                     joinInputRoles=[e['properties']['inputRole'] for e in path if 'inputRole' in e['properties']],
                     whereConditions=[s['condition'] for s in steps if s['operationType']=='FILTER'],
                     havingConditions=[s['condition'] for s in steps if s['operationType']=='HAVING'],
                     caseExpressions=[s['expressionSql'] for s in steps if s['operationType']=='CASE'])
        for name in ['selectExpressions','outputAliases','groupExpressions','aggregateExpressions']:
            props[name]=[value for s in steps for value in s.get(name,[])]
        if mutation:props['condition']=operations[-1]['properties'].get('condition','')
        identity=[source,kind,target,props['statementKey'],[e['properties']['lineageEdgeId'] for e in path],mutation]
        props['lineageEdgeId']=hashlib.sha256(json.dumps(identity,ensure_ascii=False).encode()).hexdigest()
        links.append({'from':source,'type':kind,'to':target,'properties':props})

    def visit(source,current,path,operations,statement_key=None):
        for edge in outgoing[current]:
            nxt=nodes[edge['to']]
            if nxt['label']=='SqlOperation':
                key=nxt['properties']['statementKey']
                if statement_key and key!=statement_key:continue
                visit(source,nxt['key'],path+[edge],operations+[nxt],key)
            elif nxt['label']=='SqlTable':
                assert operations
                add(source,nxt['key'],path+[edge],operations)
    for n in nodes.values():
        if n['label']=='SqlTable':visit(n['key'],n['key'],[],[])
    for e in plan['relationships']:
        if e['type'] in ('DELETES_FROM','CLEARS_TABLE'):
            add(e['to'],e['to'],[e],[nodes[e['from']]],
                'DELETE_ROWS' if e['type']=='DELETES_FROM' else 'TRUNCATE_ROWS')
    retained=[e for e in plan['relationships']
              if nodes[e['from']]['label']!='SqlOperation' and nodes[e['to']]['label']!='SqlOperation']
    result=dict(plan,nodes=[n for n in nodes.values() if n['label']!='SqlOperation'],
                relationships=retained+links,representation='table_nodes_sql_rules_on_relationships')
    assert len({e['properties']['lineageEdgeId'] for e in result['relationships']})==len(result['relationships'])
    return result
