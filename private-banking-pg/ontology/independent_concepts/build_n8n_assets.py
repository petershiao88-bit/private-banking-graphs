"""Build fixed n8n Code-node bodies from the reviewed Cypher files."""
import json
import argparse
from pathlib import Path
from concept_model import validate_plan
from mapping_routes import build_routes

HERE = Path(__file__).resolve().parent


ROOT = HERE.parents[1]


def write(directory, name, content):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(content + '\n', encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=HERE/'concept_graph.json')
    parser.add_argument('--output-dir',type=Path,default=HERE)
    args=parser.parse_args()
    plan=json.loads(args.plan.read_text(encoding='utf-8-sig'))
    validate_plan(plan)
    if plan.get('importReady') is False and args.output_dir.resolve()==HERE.resolve():
        raise RuntimeError('Review draft templates require a separate output directory')
    routes=build_routes(plan,json.loads((ROOT/'ontology/Shared_product_graph_plan.json').read_text(encoding='utf-8')),
                        json.loads((ROOT/'deliverables/mapping_review/20261012/integrated/base_tables/AUM_Income_底表映射計畫.json').read_text(encoding='utf-8')))
    emit=lambda name,content:write(args.output_dir,name,content)
    q1 = (HERE / '01_list_concepts.cypher').read_text(encoding='utf-8').strip()
    q2 = (HERE / '02_lookup_mapping.cypher').read_text(encoding='utf-8').strip()
    q3 = (HERE / '03_lookup_mapping_draft.cypher').read_text(encoding='utf-8').strip()
    emit('mapping_routes.json',json.dumps({'routes':routes,'liveVerified':False},ensure_ascii=False,indent=2))
    emit('01_request.json', json.dumps(dict(statement=q1, parameters={}), ensure_ascii=False, indent=2))
    emit('02_request.example.json', json.dumps(dict(statement=q2, parameters=dict(productCode='bank_insurance', domain='income')), ensure_ascii=False, indent=2))
    emit('n8n_01_prepare.js', '// Local template; Code node Run Once for All Items. No AI statement is accepted.\n'
          + 'const statement = ' + json.dumps(q1, ensure_ascii=False) + ';\n'
          + 'return [{json: {statement, parameters: {}}}];')
    emit('n8n_02_prepare.js', '''// Local template; must run after ConceptCatalog. Only declared measurement routes are allowed.
// ConceptCatalog is the trusted first-query projection node in this execution.
const input = $input.first().json;
if (Object.keys(input).sort().join(',') !== 'domain,productCode') {
  throw new Error('Only productCode and domain are accepted');
}
const catalog = $('ConceptCatalog').first().json.products;
if (!Array.isArray(catalog) || catalog.length === 0) throw new Error('Concept selection required');
if (typeof input.productCode !== 'string' || !catalog.some(p => p.productCode === input.productCode)) {
  throw new Error('Unknown productCode');
}
if (!['aum', 'income'].includes(input.domain)) throw new Error('Select aum or income');
const product=catalog.find(p=>p.productCode===input.productCode);
if (!Array.isArray(product[input.domain+'Metrics']) || !product[input.domain+'Metrics'].length) throw new Error('No declared measurement for this domain');
const routes = ''' + json.dumps(routes, ensure_ascii=False) + ''';
const route=routes.find(r=>r.productCode===input.productCode&&r.domain===input.domain);
if (!route) throw new Error('Mapping route unavailable');
const statements={shared_product_sql:''' + json.dumps(q2, ensure_ascii=False) + ''',mapping_draft_rules:''' + json.dumps(q3, ensure_ascii=False) + '''};
const parameters={productCode:input.productCode,domain:input.domain};
if(route.sourceGraph==='mapping_draft_rules'){parameters.productKey=route.productKey;parameters.metricKey=route.metricKey;}
return [{json: {statement:statements[route.sourceGraph], parameters}}];''')
    for name in ('n8n_01_project_output.js','n8n_02_project_output.js'):
        if args.output_dir.resolve()!=HERE.resolve():
            emit(name,(HERE/name).read_text(encoding='utf-8').strip())
    for name in ('01_list_concepts.cypher','02_lookup_mapping.cypher','03_lookup_mapping_draft.cypher','full_concept_graph_with_customer.cypher','lookup_customer_dimension.cypher','lookup_roles.cypher'):
        if args.output_dir.resolve()!=HERE.resolve():
            emit(name,(HERE/name).read_text(encoding='utf-8').strip())
    print(json.dumps({'supportedRoutes':len(routes),'sharedProductRoutes':sum(r['sourceGraph']=='shared_product_sql' for r in routes),'draftRuleRoutes':sum(r['sourceGraph']=='mapping_draft_rules' for r in routes),'onlineActions':False}))


if __name__ == '__main__':
    main()
