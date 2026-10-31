"""Audit original source preservation and semantic SQL lineage coverage."""
from collections import Counter,defaultdict,deque
import hashlib,json
from pathlib import Path
from build_sql_lineage_graph import ROOT,FILES,statements,parser_text,sqlglot,exp
from sql_table_links import LINK_TYPES


def verify(plan):
    nodes={n['key']:n for n in plan['nodes']}
    edges=plan['relationships']
    sources={n['properties']['name']:n for n in nodes.values() if n['label']=='SqlSourceFile'}
    statements_by_key={n['key']:n['properties'] for n in nodes.values() if n['label']=='SqlStatement'}
    assert not any(n['label']=='SqlOperation' for n in nodes.values())
    links_by_statement=defaultdict(list)
    for e in edges:
        if e['type'] in LINK_TYPES:
            assert nodes[e['from']]['label']==nodes[e['to']]['label']=='SqlTable'
            assert e['properties']['sql']==statements_by_key[e['properties']['statementKey']]['sql']
            links_by_statement[e['properties']['statementKey']].append(e)
    findings=[]
    for name,domain,role in FILES:
        raw=(ROOT/'sources/sql'/name).read_bytes()
        src=sources[name]['properties']
        assert src['rawSql'].encode('cp950')==raw,name
        assert src['sha256']==hashlib.sha256(raw).hexdigest()
        text=src['normalizedSql']
        for original in statements(text):
            line=text.count('\n',0,original['start'])+1
            key=f'sql_lineage:statement:{name}:L{line}'
            stored=statements_by_key[key]
            assert stored['sql']==original['sql'],key
            assert stored['lineStart']==line
            ast=sqlglot.parse_one(parser_text(original['parserSql']),read='oracle')
            if not isinstance(ast,(exp.Create,exp.Insert)):continue
            expected={'.'.join(p.name for p in t.parts).upper() for t in ast.expression.find_all(exp.Table)}
            actual={nodes[e['to']]['properties']['name'] for e in edges if e['from']==key and e['type']=='READS_TABLE'}
            assert actual==expected,(key,expected-actual,actual-expected)
            target=f"sql_lineage:table:{stored['output']}"
            for table in actual:
                start=f'sql_lineage:table:{table}'
                assert any(e['from']==start and e['to']==target for e in links_by_statement[key]),(key,table,'no direct table link')
            # Check the nested operators independently of node count.
            raw_unions=list(ast.expression.find_all(exp.Union))
            kinds={kind for e in links_by_statement[key] for kind in e['properties']['operationTypes']}
            for u in raw_unions:
                assert ('UNION' if bool(u.args.get('distinct',True)) else 'UNION ALL') in kinds
            if list(ast.expression.find_all(exp.Join)):
                assert any(k.endswith('JOIN') for k in kinds),key
            findings.append({'statement':key,'sourcesVerified':len(actual),'unionTokens':len(raw_unions)})
    def main_statement(output,filename):
        return next((k,p) for k,p in statements_by_key.items() if p['output']==output and p['file'].endswith('/'+filename) and p['status']=='active_sql')
    for output,filename,branches in [('INCOME_TMP01','9.INCOME_SMY.sql',24),('AUM','2._AUM_SUMY.sql',13)]:
        key,_=main_statement(output,filename)
        unions=[e for e in links_by_statement[key] if e['type']=='UNION']
        assert len(unions)==branches,(output,len(unions))
        assert sorted(e['properties']['unionBranchOrders'][0] for e in unions)==list(range(1,branches+1))
        assert all(e['properties']['unionDeduplication']==['exact_projected_rows'] for e in unions)
    key,_=main_statement('INCOME_TMP02','9.INCOME_SMY.sql')
    joins=links_by_statement[key]
    assert len(joins)==2 and all(e['type']=='LEFT_JOIN' for e in joins)
    assert all('cust_id' in e['properties']['joinConditions'][0].lower() and 'yyyymm' in e['properties']['joinConditions'][0].lower() for e in joins)
    assert sorted(e['properties']['joinInputRoles'][0] for e in joins)==['left','right']
    assert nodes['sql_lineage:table:AUM_TMP02']['properties']['definitionStatus']=='alternate_or_auxiliary_definition'
    assert nodes['sql_lineage:table:AUM_005_007_008_009_TMP01']['properties']['definitionStatus']=='commented_definition_only'
    assert nodes['sql_lineage:table:INCOME_066_TMP01']['properties']['definitionStatus']=='commented_definition_only'
    assert any(p['statementType']=='DELETE' and p['output']=='INCOME_066' for p in statements_by_key.values())
    assert any(p['statementType']=='INSERT' and p['output']=='INCOME_066' for p in statements_by_key.values())
    return {'sourceFilesByteRoundTrip':len(sources),'statementsExactSlices':len(statements_by_key),
            'dataProducingStatementsAudited':len(findings),'allReadTablesReachOutputs':True,
            'incomeUnionBranches':24,'aumUnionBranches':13,'incomeCustomerJoinVerified':True,
            'historyAndAlternateDefinitionsSeparated':True,'monthlyDeleteInsertPreserved':True,
            'operationNodes':0,'tableLinkTypes':dict(Counter(e['type'] for e in edges if e['type'] in LINK_TYPES))}


if __name__=='__main__':
    p=json.loads((ROOT/'ontology/SQL_lineage_graph_plan.json').read_text(encoding='utf-8'))
    report=verify(p)
    (ROOT/'ontology/SQL_lineage_plan_validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
