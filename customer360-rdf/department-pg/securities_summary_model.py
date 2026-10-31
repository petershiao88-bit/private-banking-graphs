"""Reviewed summary scopes; component membership is not an executable SUM rule."""
import copy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('securities_summary_common', HERE/'advisory_income_model.py')
common = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(common)
FH, SEC = common.FH, 'https://example.org/ontology/securities#'
require, keys, canonical_json = common.require, common.keys, common.canonical_json
LABELS = common.LABELS
RELATIONSHIPS = {**common.RELATIONSHIPS, 'HAS_COMPONENT_METRIC': ('BusinessConcept', 'BusinessConcept')}
CONTRACT = {
    'securities.total_aum': ('私銀－證券總 AUM', 'aum', 'SecuritiesAUM',
        {'securities.bond_aum','securities.structured_aum','securities.fund_aum',
         'securities.foreign_stock_aum','securities.taiwan_stock_aum'},
        {'amount','currency','aumAsOfDate'}, {'securities.stock_pledge_aum'}),
    'securities.total_fee_income': ('私銀－證券總手收', 'fee_income', 'SecuritiesFeeIncome',
        {'securities.bond_fee_income','securities.structured_fee_income',
         'securities.fund_fee_income','securities.foreign_stock_fee_income'},
        {'amount','currency','incomePeriodStart','incomePeriodEnd'}, {'securities.taiwan_stock_fee_income'}),
}
FIELDS = {k: common.FIELDS[k] for k in {'amount','currency','aumAsOfDate','incomePeriodStart','incomePeriodEnd'}}
EXECUTION = {'sql','join_rules','filter_rules','aggregation_rules','row_grain','snapshot_selection',
             'currency_conversion','deduplication_rules','recognition_rules','period_basis'}


def validate_model(model, metric_concepts=None):
    keys(model, {'schema_version','ontology_version','status','scope','inference','instance_mapping',
                 'access_policy_status','field_definitions','execution','evidence','concepts','relation_definitions'},
         'securities summaries')
    require((model['schema_version'],model['ontology_version'],model['status'],model['scope']) ==
            ('1.0.0','0.16.0','active','metadata_only'), 'Expected active summary scope on RDF v0.16.0')
    require(model['inference'] is False and model['instance_mapping'] is False and
            model['access_policy_status']=='deferred_by_user', 'No instances, inference or access decisions')
    keys(model['execution'],EXECUTION,'summary execution')
    require(all(v is None for v in model['execution'].values()), 'Calculation and source rules belong to Tool')
    keys(model['field_definitions'],FIELDS,'summary fields')
    for field, semantics in FIELDS.items():
        d=model['field_definitions'][field]
        keys(d,{'name','definition','data_type_hint','property_uri','entity_class_uri'},'summary field')
        require(tuple(d[k] for k in ('data_type_hint','property_uri','entity_class_uri'))==semantics,
                'Incorrect amount/date/period semantics')
        require(all(isinstance(d[k],str) and d[k].strip() for k in ('name','definition')), 'Missing field meaning')
    evidence=model['evidence']
    require(isinstance(evidence,dict) and bool(evidence),'Missing SQL scope evidence')
    for e in evidence.values():
        require(isinstance(e,dict) and isinstance(e.get('file'),str) and
                e['file'].startswith('Ontology/私銀智能問答/') and '..' not in Path(e['file']).parts,
                'Invalid source path')

    def refs(values):
        require(isinstance(values,list) and bool(values) and len(values)==len(set(values)) and
                all(isinstance(v,str) and v in evidence for v in values), 'Invalid summary evidence')

    require(model['relation_definitions']==[], 'Membership is PG metadata, not a new RDF property or advisor relation')
    concepts=model['concepts']
    require(isinstance(concepts,list) and len(concepts)==len(CONTRACT), 'Expected only the two approved totals')
    seen=set()
    for c in concepts:
        keys(c,{'id','name','definition','subsidiary','department_owner','class_uri','specific_product_class_uri',
                'metric_kind','coverage_status','lineage_mode','calculation_status','component_metric_ids',
                'excluded_metric_ids','fields','observations'},'summary concept')
        cid=c['id']
        require(isinstance(cid,str) and cid in CONTRACT and cid not in seen,'Unexpected or duplicate summary')
        seen.add(cid)
        name,kind,cls,components,fields,excluded=CONTRACT[cid]
        require((c['name'],c['metric_kind'],c['class_uri'],c['subsidiary'],c['department_owner'],
                 c['specific_product_class_uri'],c['coverage_status'],c['lineage_mode'],c['calculation_status']) ==
                (name,kind,SEC+cls,'securities',None,None,'included_products_only','via_component_metrics','pending_tool_definition'),
                'Preserve securities source, limited coverage and pending calculation')
        require(isinstance(c['definition'],str) and c['definition'].strip(),'Missing limited-scope definition')
        for key,expected in (('component_metric_ids',components),('excluded_metric_ids',excluded)):
            values=c[key]
            require(isinstance(values,list) and len(values)==len(expected) and
                    all(isinstance(v,str) for v in values) and set(values)==expected,
                    'Wrong, duplicated, excluded or recursive summary component')
        if metric_concepts is not None:
            for component_id in components:
                component=metric_concepts.get(component_id)
                require(isinstance(component,dict) and component.get('class_uri')==SEC+cls and
                        component.get('subsidiary')=='securities' and 'table_sources' in component and
                        'component_metric_ids' not in component, 'Summary components must be original active securities metrics')
        require(isinstance(c['fields'],list) and len(c['fields'])==len(fields), 'Incorrect aggregate result fields')
        field_seen=set()
        for f in c['fields']:
            keys(f,{'field','status','table','column','candidates'},'summary mapping')
            require(isinstance(f['field'],str) and f['field'] in fields and f['field'] not in field_seen,
                    'Unexpected or duplicate aggregate field')
            field_seen.add(f['field'])
            require((f['status'],f['table'],f['column'],f['candidates'])==('pending',None,None,[]),
                    'No summary column mapping or inherited input candidates')
        obs=c['observations']
        keys(obs,{'coverage','sql_behavior_observation','amount_observation','date_observation','gaps','evidence'},
             'summary observations')
        require(all(isinstance(obs[k],str) and obs[k].strip() for k in
                    ('coverage','sql_behavior_observation','amount_observation','date_observation')), 'Missing scope observation')
        require(isinstance(obs['gaps'],list) and bool(obs['gaps']) and
                all(isinstance(v,str) and v.strip() for v in obs['gaps']), 'Keep unresolved aggregate behavior')
        refs(obs['evidence'])


def load_model(path=None):
    model=json.loads((HERE/'securities-summary-metrics.json' if path is None else Path(path)).read_text(encoding='utf-8'))
    validate_model(model)
    return model


def build_graph(model, metric_concepts):
    validate_model(model,metric_concepts)
    m=copy.deepcopy(model)
    for c in m['concepts']:
        for key in ('component_metric_ids','excluded_metric_ids'):c[key].sort()
        c['observations']['evidence'].sort()
    graph=common.project_graph(m,'department-pg.securities-summary-metrics')
    nodes={n['id']:n for n in graph['nodes']}
    edges={e['id']:e for e in graph['relationships']}
    nodes['department-pg.securities-summary-metrics']['properties']['evidence_json']=canonical_json(m['evidence'])
    for c in m['concepts']:
        cid=c['id']
        nodes[cid]['properties'].update(metric_kind=c['metric_kind'],coverage_status=c['coverage_status'],
            lineage_mode=c['lineage_mode'],calculation_status=c['calculation_status'],
            component_metric_ids_json=canonical_json(c['component_metric_ids']),
            excluded_metric_ids_json=canonical_json(c['excluded_metric_ids']),
            observations_json=canonical_json(c['observations']))
        for component in c['component_metric_ids']:
            eid=cid+'|HAS_COMPONENT_METRIC|'+component
            edges[eid]={'id':eid,'type':'HAS_COMPONENT_METRIC','source':cid,'target':component}
    return {'nodes':sorted(nodes.values(),key=lambda n:n['id']),
            'relationships':sorted(edges.values(),key=lambda e:e['id'])}
