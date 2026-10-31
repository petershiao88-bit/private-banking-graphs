"""Bank collective/ETF/insurance/fund and securities metadata; source evidence never approves execution rules."""
import copy
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('investment_common', HERE / 'advisory_income_model.py')
common = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(common)
FH, BANK = common.FH, common.BANK
SEC = 'https://example.org/ontology/securities#'
require, keys, canonical_json = common.require, common.keys, common.canonical_json
LABELS = common.LABELS | {'SourceTable'}
RELATIONSHIPS = {**common.RELATIONSHIPS, 'CANDIDATE_SOURCE':('DataFieldDefinition','SourceTable')}
CONTRACT = {
    'bank.fund_aum':('bank_fund', 'FundProduct'),
    'bank.fund_fee_income':('bank_fund', 'FundProduct'),
    'bank.collective_account_aum':('bank_collective_account', 'CollectiveManagementProduct'),
    'bank.etf_aum':('bank_etf', 'ETFProduct'),
    'bank.etf_fee_income':('bank_etf', 'ETFProduct'),
    'bank.insurance_aum':('bank_insurance', 'InsuranceProduct'),
    'bank.insurance_fee_income':('bank_insurance', 'InsuranceProduct'),
    'securities.bond_aum':('securities_bond','BondProduct','OverseasFinancialProduct'),
    'securities.bond_fee_income':('securities_bond','BondProduct','OverseasFinancialProduct'),
    'securities.structured_aum':('securities_structured','StructuredFinancialProduct'),
    'securities.structured_fee_income':('securities_structured','StructuredFinancialProduct'),
    'securities.fund_aum':('securities_fund','FundProduct'),
    'securities.fund_fee_income':('securities_fund','FundProduct'),
    'securities.foreign_stock_aum':('securities_foreign_stock','StockProduct','OverseasFinancialProduct'),
    'securities.foreign_stock_fee_income':('securities_foreign_stock','StockProduct','OverseasFinancialProduct'),
    'securities.taiwan_stock_aum':('securities_taiwan_stock','StockProduct'),
}
EXECUTION = {'sql','join_rules','filter_rules','aggregation_rules','row_grain','valuation_rules',
             'snapshot_selection','currency_conversion','deduplication_rules','aum_recognition_rules',
             'fee_recognition_rules','attribution_rules','period_basis'}
INSURANCE_TABLES = {
    'bank.insurance_aum': 'DSKPI.AFAUM_AFCUST_MON_ASSET_REPORT',
    'bank.insurance_fee_income': 'DSINS.INSU_RPT_Q01',
}

TABLE_ONLY_TABLES = {**INSURANCE_TABLES,
    'bank.collective_account_aum': 'DSFND.PB_FUND_MONTH',
    'bank.etf_aum': 'DSFND.PB_FUND_MONTH',
    'bank.etf_fee_income': 'DSFND.PB_FUND_SPREAD_DAILY',
}


def expected_inputs(cid):
    """Bounded observed input roles, including account/customer and AM source conflicts."""
    if cid in TABLE_ONLY_TABLES:
        return {}  # New bank metrics are table-level only; all physical field mappings stay empty.
    if cid == 'bank.fund_aum':
        return {k:{('DSFND.PB_FUND_MONTH',col)} for k,col in (
            ('customerId','IDNO'),('amount','CurrentTWDValue'),('snapshotDate','EXEDATE'))}
    if cid == 'bank.fund_fee_income':
        return {k:{('DSFND.PB_FUND_SPREAD_DAILY',col) for col in columns} for k,columns in {
            'customerId':['IDNO'],'amount':['BRHREBATEAMT'],'productId':['FUNDID'],
            'incomePeriod':['FEEDATE'],'employeeId':['BAOEMPID','SAOEMPID']}.items()}
    aum = cid.endswith('_aum')
    if '.bond_' in cid or '.structured_' in cid:
        stem='PB_BONDPOS_SEC' if aum else 'PB_BONDTRADM_SEC'
        customer=['IDNO'];amount=['NETQTY','CPRICE'] if aum else ['CFEE','FXRATE']
        dates=['CLRDATE']
    elif '.fund_' in cid:
        stem='PB_FUNDPOSIT_SEC' if aum else 'PB_FUNDTRADM_SEC'
        customer=['WKB02'] if aum else ['WKA28']
        amount=['WKB28','WKB23','WKB31'] if aum else ['WKA31']
        dates=['YYYYMMDD'] if aum else ['WKA02']
    elif '.taiwan_stock_' in cid:
        stem='PB_YTRMRBP_SEC';customer=['YTRMRB025'];amount=['YTRMRB110','YTRMRB150'];dates=['YYYYMMDD']
    else:
        stem='PB_STOCKPOS_SEC' if aum else 'PB_STOCKTRADM_PM_SEC'
        customer=['IDNO'];amount=['NETQTY','CPRICE'] if aum else ['CFEE','ABFEE','FXRATE'];dates=['CLRDATE']
    tables=['DSPBM.'+stem+'_M','DSPBM.'+stem]
    if '.foreign_stock_' in cid and not aum:
        tables.append('DSPBM.PB_STOCKTRADM_AM_SEC_M')
    result={k:{(t,col) for t in tables for col in cols} for k,cols in (
        ('customerId',customer),('amount',amount),('snapshotDate' if aum else 'incomePeriod',dates))}
    if aum and ('.bond_' in cid or '.structured_' in cid or '.foreign_stock_' in cid):
        result['amount'].add(('DSDEP.FN_EXCH_RT','EXCH_RT'))
        result['snapshotDate']={(tables[1],'CLRDATE'),('DSDEP.FN_EXCH_RT','PRCS_DT')}
        if '.foreign_stock_' not in cid:
            result['snapshotDate'].add((tables[0],'PRCS_DT'))
    if cid=='securities.fund_aum':
        result['customerId'].add(('DSPBM.PB_FUNDPOSIT_SEC','WKB24'))
    return result


def validate_model(model):
    keys(model, {'schema_version','ontology_version','status','scope','inference','instance_mapping',
                 'access_policy_status','field_definitions','execution','evidence','sources',
                 'concepts','relation_definitions','pending_scope'}, 'investment metrics')
    require((model['schema_version'],model['ontology_version'],model['status'],model['scope']) ==
            ('1.0.0','0.13.0','active','metadata_only') and model['inference'] is False and
            model['instance_mapping'] is False, 'Expected v0.13 metadata without instances/inference')
    require(model['access_policy_status'] == 'deferred_by_user','Access remains deferred')
    keys(model['execution'],EXECUTION,'execution')
    require(all(v is None for v in model['execution'].values()),'No execution/recognition/attribution rules approved')
    keys(model['field_definitions'],common.FIELDS,'fields')
    for field, semantics in common.FIELDS.items():
        definition = model['field_definitions'][field]
        keys(definition, {'name','definition','data_type_hint','property_uri','entity_class_uri'},'field definition')
        require(tuple(definition[k] for k in ('data_type_hint','property_uri','entity_class_uri')) == semantics,
                'Incorrect field semantic reference')
        require(all(isinstance(definition[k],str) and definition[k].strip() for k in ('name','definition')),
                'Missing field name/definition')
    evidence = model['evidence']
    require(isinstance(evidence,dict) and bool(evidence),'Missing evidence')

    def refs(values):
        require(isinstance(values,list) and bool(values) and all(isinstance(v,str) and v in evidence for v in values)
                and len(values)==len(set(values)),'Invalid evidence reference')

    for item in evidence.values():
        require(isinstance(item,dict) and isinstance(item.get('file'),str)
                and item['file'].startswith('Ontology/私銀智能問答/') and '..' not in Path(item['file']).parts,
                'Invalid source evidence path')
    sources = model['sources']
    require(isinstance(sources,list) and bool(sources),'Missing sources')
    tables = set()
    for source in sources:
        keys(source, {'table','status','database_verified','evidence'},'source')
        table = source['table']
        require(isinstance(table,str) and table not in tables and source['status']=='observed_in_files'
                and source['database_verified'] is False,'Duplicate or falsely verified source')
        tables.add(table)
        refs(source['evidence'])
    concepts = model['concepts']
    require(isinstance(concepts,list) and len(concepts)==len(CONTRACT),'Incorrect investment coverage')
    seen = set()
    for c in concepts:
        keys(c, {'id','name','definition','subsidiary','department_owner','class_uri',
                 'specific_product_class_uri','product_class_uris','metric_kind','product_code','fields','observations','table_sources'},'concept')
        cid = c['id']
        require(isinstance(cid,str) and cid in CONTRACT and cid not in seen,'Unknown/duplicate concept')
        seen.add(cid)
        subsidiary = cid.split('.')[0]
        ns = BANK if subsidiary=='bank' else SEC
        aum = cid.endswith('_aum')
        observed_tables = {table for table, column in expected_inputs(cid).get('amount', set())}
        expected_tables = {(table, 'valuation_support' if table == 'DSDEP.FN_EXCH_RT' else 'primary')
                           for table in observed_tables}
        if cid in TABLE_ONLY_TABLES:
            expected_tables = {(TABLE_ONLY_TABLES[cid], 'primary')}
        if cid == 'securities.fund_fee_income':
            expected_tables.add(('DSPBM.PB_BONDTRADM_SEC', 'date_lookup_only'))
        if cid == 'securities.foreign_stock_fee_income':
            expected_tables.add(('DSPBM.PB_STOCKTRADM_AM_SEC', 'date_lookup_only'))
        common.validate_table_sources(c['table_sources'], evidence, sources, expected_tables,
                                      partial=cid == 'bank.insurance_fee_income')
        helpers = c['table_sources']['unresolved_supporting_relations']
        require(len(helpers) == (1 if subsidiary == 'securities' and not aum else 0),
                'Retain observed calendar relation without inventing its physical table')
        cls = ('Bank' if subsidiary=='bank' else 'Securities') + ('AUM' if aum else 'FeeIncome')
        code,*products = CONTRACT[cid]
        require(c['metric_kind']==('aum' if aum else 'fee_income') and c['class_uri']==ns+cls
                and c['subsidiary']==subsidiary and c['product_code']==code
                and c['department_owner'] is None and c['specific_product_class_uri'] is None
                and isinstance(c['product_class_uris'],list)
                and sorted(c['product_class_uris'])==sorted(ns+p for p in products),'Incorrect metric/subsidiary/product semantics')
        require(all(isinstance(c[k],str) and c[k].strip() for k in ('name','definition')),'Missing concept definition')
        fields = {'customerId','productId','amount','currency','snapshotDate'}
        if not aum:
            fields.add('incomePeriod')
            if subsidiary=='bank': fields.add('employeeId')
        fields.update(common.AUM_ELEMENTS if aum else common.FEE_ELEMENTS)
        require(isinstance(c['fields'],list) and len(c['fields'])==len(fields),'Incorrect metric field coverage')
        actual = set()
        inputs = expected_inputs(cid)
        for f in c['fields']:
            keys(f, {'field','status','table','column','candidates'},'mapping')
            field = f['field']
            require(isinstance(field,str) and field in fields and field not in actual,'Unknown/duplicate metric field')
            actual.add(field)
            status = 'pending' if cid in TABLE_ONLY_TABLES or field in (common.AUM_ELEMENTS | common.FEE_ELEMENTS) else {'amount':'pending_aum_recognition' if aum else 'pending_fee_recognition',
                      'customerId':'pending_identity_review','productId':'pending_product_identity',
                      'currency':'pending_currency','snapshotDate':'pending_time_semantics',
                      'incomePeriod':'pending_period_basis','employeeId':'pending_advisor_attribution'}[field]
            require(f['status']==status and f['table'] is None and f['column'] is None,'Mapping must remain pending')
            require(isinstance(f['candidates'],list),'Candidates must be a list')
            if field=='currency' or (not aum and field=='snapshotDate'):
                require(f['candidates']==[],'No approved currency or fee snapshot candidate')
            if field=='productId' and cid!='bank.fund_fee_income':
                require(f['candidates']==[],'Do not invent a product identifier from classification')
            pairs=set()
            for candidate in f['candidates']:
                keys(candidate, {'table','column','meaning','evidence'},'candidate')
                pair=(candidate['table'],candidate['column'])
                require(candidate['table'] in tables and isinstance(candidate['column'],str)
                        and candidate['column'].strip() and pair not in pairs,'Unknown/duplicate source input')
                pairs.add(pair)
                require(isinstance(candidate['meaning'],str) and candidate['meaning'].strip(),'Missing input meaning')
                refs(candidate['evidence'])
                require((subsidiary=='bank' and candidate['table'].startswith('DSFND.'))
                        or (subsidiary=='securities' and (candidate['table'].startswith('DSPBM.')
                            or candidate['table']=='DSDEP.FN_EXCH_RT')),
                        'Do not mix subsidiary metric sources')
            require(pairs == inputs.get(field,set()),'Incorrect observed input roles or missing valuation components')
        obs=c['observations']
        keys(obs, {'coverage','classification_observation','valuation_observation','date_observation','gaps','evidence'},'observations')
        require(all(isinstance(obs[k],str) and obs[k].strip() for k in (
            'coverage','classification_observation','valuation_observation','date_observation')),'Missing source observation')
        require(isinstance(obs['gaps'],list) and bool(obs['gaps']) and all(isinstance(v,str) and v.strip() for v in obs['gaps']),
                'Missing unresolved scope')
        refs(obs['evidence'])
    relations=model['relation_definitions']
    require(isinstance(relations,list) and len(relations)==len(CONTRACT)+3,'Incorrect relation coverage')
    expected={cid+'.product' for cid in CONTRACT}|{'bank.fund_fee_income.advisor', 'bank.insurance_fee_income.advisor', 'bank.etf_fee_income.advisor'}
    seen=set()
    for r in relations:
        keys(r, {'id','name','source_concept','property_uri','domain_uri','target_class_uri','fields'},'relation')
        rid=r['id']
        require(isinstance(rid,str) and rid in expected and rid not in seen,'Unknown/duplicate relation')
        seen.add(rid)
        cid=rid.rsplit('.',1)[0]
        if rid.endswith('.advisor'):
            expected_refs=(BANK+'attributedToAdvisor',BANK+'BankFeeIncome',BANK+'FinancialAdvisor')
        else:
            aum=cid.endswith('_aum')
            expected_refs=(FH+('measuresProduct' if aum else 'feeIncomeFromProduct'),
                           FH+('AUM' if aum else 'FeeIncome'),FH+'FinancialProduct')
        require(r['source_concept']==cid and r['fields']==[] and
                tuple(r[k] for k in ('property_uri','domain_uri','target_class_uri'))==expected_refs,
                'Incorrect product domain or bank-only advisor attribution')
        require(isinstance(r['name'],str) and r['name'].strip(),'Missing relation name')
    pending=model['pending_scope']
    require(isinstance(pending,list) and len(pending)==3,'Missing deferred scope')
    seen=set()
    statuses={'securities.taiwan_stock_fee_income':'pending_source_definition',
              'securities.stock_pledge':'pending_business_semantics',
              'bank.collective_account_fee_income':'pending_business_semantics'}
    for item in pending:
        keys(item, {'id','status','reason','evidence'},'pending scope')
        require(item['id'] in statuses and item['id'] not in seen and item['status']==statuses[item['id']]
                and isinstance(item['reason'],str) and item['reason'].strip(),'Incorrect deferred scope')
        seen.add(item['id'])
        refs(item['evidence'])


def load_model(path=None):
    model=json.loads((HERE/'investment-metrics.json' if path is None else Path(path)).read_text(encoding='utf-8'))
    validate_model(model)
    return model


def build_graph(model):
    validate_model(model)
    model=copy.deepcopy(model)
    for item in model['evidence'].values():
        if 'rows' in item: item['rows'].sort()
    for item in model['pending_scope']: item['evidence'].sort()
    for c in model['concepts']:
        c['observations']['evidence'].sort()
        for f in c['fields']:
            for item in f['candidates']: item['evidence'].sort()
            f['candidates'].sort(key=canonical_json)
    graph=common.project_graph(model,'department-pg.investment-metrics')
    nodes={n['id']:n for n in graph['nodes']}
    edges={e['id']:e for e in graph['relationships']}
    nodes['department-pg.investment-metrics']['properties'].update(
        evidence_json=canonical_json(model['evidence']),
        pending_scope_json=canonical_json(sorted(model['pending_scope'],key=lambda v:v['id'])))

    def edge(source,kind,target):
        eid=source+'|'+kind+'|'+target
        edges[eid]={'id':eid,'type':kind,'source':source,'target':target}

    for s in model['sources']:
        sid='source:'+s['table']
        nodes[sid]={'id':sid,'label':'SourceTable','properties':{'scope':'metadata_only','table':s['table'],
            'status':s['status'],'database_verified_json':'false','evidence_json':canonical_json(sorted(s['evidence']))}}
    for c in model['concepts']:
        cid=c['id']
        nodes[cid]['properties'].update(observations_json=canonical_json(c['observations']),
            product_class_uris_json=canonical_json(sorted(c['product_class_uris'])),
            product_code=c['product_code'],metric_kind=c['metric_kind'])
        for uri in c['product_class_uris']:
            nodes[uri]={'id':uri,'label':'OntologyClassReference','properties':{'scope':'metadata_only','uri':uri}}
            edge(cid+'.product','HAS_TARGET_CLASS',uri)
        for f in c['fields']:
            for table in {v['table'] for v in f['candidates']}:
                edge(cid+'.'+f['field'],'CANDIDATE_SOURCE','source:'+table)
    return {'nodes':sorted(nodes.values(),key=lambda n:n['id']),
            'relationships':sorted(edges.values(),key=lambda e:e['id'])}
