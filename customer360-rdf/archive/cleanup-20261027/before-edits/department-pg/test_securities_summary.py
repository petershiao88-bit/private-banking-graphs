"""Bounded summary membership and inherited lineage, with calculations still deferred."""
import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDFS
from test_bank_business import builder
from test_product_fees import source_path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BEFORE = ROOT/'archive/before-securities-summary-20261024'
SUMMARY_IDS = {'securities.total_aum','securities.total_fee_income'}
AUM_IDS = {'securities.bond_aum','securities.structured_aum','securities.fund_aum',
           'securities.foreign_stock_aum','securities.taiwan_stock_aum'}
FEE_IDS = {'securities.bond_fee_income','securities.structured_fee_income',
           'securities.fund_fee_income','securities.foreign_stock_fee_income'}


def components():
    return {c['id']:c for c in builder.investment_metrics.load_model()['concepts'] if c['subsidiary']=='securities'}


class SecuritiesSummaryTests(unittest.TestCase):
    def setUp(self):
        self.model=builder.securities_summary.load_model()
        self.concepts={c['id']:c for c in self.model['concepts']}

    def test_exact_limited_memberships_exclusions_and_common_metric_classes(self):
        self.assertEqual(set(self.concepts),SUMMARY_IDS)
        for cid,expected,kind,cls,excluded in (
            ('securities.total_aum',AUM_IDS,'aum','SecuritiesAUM',{'securities.stock_pledge_aum'}),
            ('securities.total_fee_income',FEE_IDS,'fee_income','SecuritiesFeeIncome',{'securities.taiwan_stock_fee_income'})):
            c=self.concepts[cid]
            self.assertEqual(set(c['component_metric_ids']),expected)
            self.assertEqual(c['metric_kind'],kind)
            self.assertEqual(c['class_uri'],builder.securities_summary.SEC+cls)
            self.assertEqual(set(c['excluded_metric_ids']),excluded)
            self.assertEqual(c['coverage_status'],'included_products_only')
            self.assertEqual(c['calculation_status'],'pending_tool_definition')
            self.assertNotIn('table_sources',c)
            self.assertTrue(any('全部業務' in gap for gap in c['observations']['gaps']))
        self.assertEqual(self.model['relation_definitions'],[])

    def test_rdf_sources_seven_original_models_and_prior_history_remain_byte_identical(self):
        for fn in ('holding-core.ttl','bank-common.ttl','bank-deposit.ttl','bank-investment-products.ttl',
                   'securities-common.ttl','customer360-ontology.ttl','customer360-ontology.owl','build-config.json','catalog-v001.xml'):
            self.assertEqual((ROOT/fn).read_bytes(),(BEFORE/fn).read_bytes(),fn)
        for name in ('model','deposits','advisory-income','product-fees','product-aum','investment-metrics','bank-business-metrics'):
            fn=name+'.json'
            self.assertEqual((HERE/fn).read_bytes(),(BEFORE/'department-pg'/fn).read_bytes(),fn)
        old=json.loads((BEFORE/'department-pg/departments.json').read_text(encoding='utf-8'))
        now=builder.departments.load_model()
        self.assertEqual(set(now['metric_ids'])-set(old['metric_ids']),SUMMARY_IDS)
        normalized=copy.deepcopy(now);normalized['metric_ids']=old['metric_ids']
        self.assertEqual(normalized,old)
        for p in (BEFORE/'department-pg/history').glob('*.json'):
            self.assertEqual(p.read_bytes(),(HERE/'history'/p.name).read_bytes(),p.name)

    def test_existing_nodes_edges_and_all_component_source_roles_survive(self):
        spec=importlib.util.spec_from_file_location('before_summary_builder',BEFORE/'department-pg/build_cypher.py')
        old_builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(old_builder)
        old=old_builder.build_combined_graph();now=builder.build_combined_graph()
        nodes={n['id']:n for n in now['nodes']};edges={e['id']:e for e in now['relationships']}
        for n in old['nodes']:
            current=copy.deepcopy(nodes[n['id']])
            if n['id']=='department-pg.departments':
                current['properties']['metric_ids_json']=n['properties']['metric_ids_json']
            self.assertEqual(current,n,n['id'])
        for e in old['relationships']:self.assertEqual(e,edges[e['id']])
        for cid,c in components().items():
            for row in c['table_sources']['tables']:
                kind=builder.advisory_income.TABLE_ROLES[row['role']]
                eid=cid+'|'+kind+'|source:'+row['table']
                self.assertIn(eid,edges)

    def test_summary_adoption_and_lineage_are_connected_without_direct_source_or_advisor_edges(self):
        g=builder.build_combined_graph()
        edges={(e['source'],e['type'],e['target']) for e in g['relationships']}
        membership={(s,t) for s,k,t in edges if k=='HAS_COMPONENT_METRIC'}
        self.assertEqual(membership,{('securities.total_aum',t) for t in AUM_IDS} |
                         {('securities.total_fee_income',t) for t in FEE_IDS})
        self.assertEqual(len(membership),9)
        for cid,c in self.concepts.items():
            self.assertIn(('bank.private_banking','USES_METRIC',cid),edges)
            for target in c['component_metric_ids']:
                self.assertFalse(any(s==target and k=='HAS_COMPONENT_METRIC' for s,k,t in edges))
            self.assertFalse(any(s==cid and k in {'HAS_SOURCE_TABLE','USES_VALUATION_SOURCE','USES_DATE_LOOKUP_SOURCE',
                                                'HAS_RELATION_DEFINITION'} for s,k,t in edges))
        self.assertEqual(sum(k=='USES_METRIC' for s,k,t in edges),44)
        self.assertEqual(sum(n['label']=='SourceTable' for n in g['nodes']),52)

    def test_seven_result_fields_resolve_to_correct_rdf_domains_without_valuation_inputs(self):
        rdf=Graph().parse(ROOT/'customer360-ontology.ttl',format='turtle')
        expected={'securities.total_aum':{'amount','currency','aumAsOfDate'},
                  'securities.total_fee_income':{'amount','currency','incomePeriodStart','incomePeriodEnd'}}
        self.assertEqual(sum(len(c['fields']) for c in self.concepts.values()),7)
        for cid,c in self.concepts.items():
            self.assertEqual({f['field'] for f in c['fields']},expected[cid])
            ancestors=set(rdf.transitive_objects(URIRef(c['class_uri']),RDFS.subClassOf))
            for f in c['fields']:
                self.assertEqual((f['status'],f['table'],f['column'],f['candidates']),('pending',None,None,[]))
                d=self.model['field_definitions'][f['field']]
                if d['property_uri']:
                    self.assertIn(rdf.value(URIRef(d['property_uri']),RDFS.domain),ancestors)
        self.assertTrue(all(v is None for v in self.model['execution'].values()))

    def test_scope_evidence_preserves_mixed_pledge_label_draft_dates_net_fee_and_union(self):
        def text(eid):
            r=self.model['evidence'][eid];start,end=r['lines']
            return '\n'.join(source_path(r).read_text(encoding=r['encoding']).splitlines()[start-1:end]).upper()
        mixed=text('aum_summary_pledge_mixed_as_taiwan')
        for token in ('AUM_027','AUM_028',"'台股'",'UNION'):self.assertIn(token,mixed)
        fee=text('income_detail_components')
        for token in ('CFEE-ABFEE','LAST2_WD','ADD_MONTHS','UNION','PB_STOCKTRADM_AM_SEC_M'):self.assertIn(token,fee)
        r=self.model['evidence']['aum_monthly_query_draft']
        d=json.loads(source_path(r).read_text(encoding='utf-8-sig'))
        self.assertEqual(next(x for x in d['metrics'] if x['code']=='aum_total_month_end')['status'],'draft_metric_query')
        self.assertEqual(r['status'],'draft_metric_query')
        self.assertTrue(any('完整產製' in s for s in self.concepts['securities.total_aum']['observations']['gaps']))
        self.assertIn('淨手收',self.concepts['securities.total_fee_income']['observations']['amount_observation'])

    def test_invalid_components_mappings_complete_coverage_or_executable_rules_are_rejected(self):
        for change in ('bank','pledge','taiwan_fee','recursive','duplicate','missing','class','coverage','status',
                       'lineage','table','candidate','sql','period','advisor','source_owner'):
            m=copy.deepcopy(self.model);c=next(c for c in m['concepts'] if c['id']=='securities.total_aum')
            if change in {'bank','pledge','recursive'}:
                c['component_metric_ids'][0]={'bank':'bank.fund_aum','pledge':'securities.stock_pledge_aum',
                                               'recursive':'securities.total_aum'}[change]
            elif change=='taiwan_fee':m['concepts'][1]['component_metric_ids'][0]='securities.taiwan_stock_fee_income'
            elif change=='duplicate':c['component_metric_ids'][0]=c['component_metric_ids'][1]
            elif change=='missing':c['component_metric_ids'].pop()
            elif change=='class':c['class_uri']=builder.FH+'AUM'
            elif change=='coverage':c['coverage_status']='complete_securities_company'
            elif change=='status':c['calculation_status']='executable'
            elif change=='lineage':c['table_sources']={'tables':[]}
            elif change=='table':c['fields'][0]['table']='AUM_REPORT'
            elif change=='candidate':c['fields'][0]['candidates']=[{'column':'AMT'}]
            elif change=='sql':m['execution']['sql']='SELECT SUM(AMT) FROM AUM'
            elif change=='period':c['fields'][2]['field']='incomePeriodStart'
            elif change=='advisor':m['relation_definitions']=[{'property_uri':'bank:attributedToAdvisor'}]
            else:c['department_owner']='私人銀行'
            with self.subTest(change=change),self.assertRaises(ValueError):builder.render_combined_cypher(summary_model=m)
        comp=components();comp['securities.fund_aum']['class_uri']=builder.FH+'FinancialProduct'
        with self.assertRaises(ValueError):builder.securities_summary.build_graph(self.model,comp)

    def test_projection_is_deterministic_and_source_inventory_marks_inherited_roles(self):
        changed=copy.deepcopy(self.model);changed['concepts'].reverse()
        for c in changed['concepts']:
            c['fields'].reverse();c['component_metric_ids'].reverse();c['observations']['evidence'].reverse()
        self.assertEqual(builder.render_combined_cypher(),builder.render_combined_cypher(summary_model=changed))
        self.assertEqual(builder.render_combined_cypher().encode('utf-8'),(HERE/'model.cypher').read_bytes())
        spec=importlib.util.spec_from_file_location('summary_inventory',ROOT/'tools/export_metric_tables.py')
        exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)
        report=exporter.render()
        self.assertEqual(report.encode('utf-8'),(HERE/'METRIC-TABLE-SOURCES.md').read_bytes())
        self.assertIn('44 項指標',report)
        for name in ('私銀－證券總 AUM','私銀－證券總手收'):
            row=next(line for line in report.splitlines() if line.startswith('| '+name+' |'))
            self.assertIn('沿分項追溯',row)
            self.assertNotIn('DSCSD.PBCMS_REPORTA03',row)
        row=next(line for line in report.splitlines() if line.startswith('| 私銀－證券總手收 |'))
        cells=row.split('|')
        self.assertIn('PB_BONDTRADM_SEC',cells[2])
        self.assertIn('PB_BONDTRADM_SEC',cells[3])
        self.assertIn('PB_STOCKTRADM_AM_SEC`',cells[3])
        self.assertNotIn('PB_STOCKTRADM_AM_SEC`',cells[2])

    def test_original_sources_and_reviewed_evidence_hashes_remain_unchanged(self):
        hashes=json.loads((BEFORE/'source-readonly-sha256.json').read_text(encoding='utf-8'))
        for relative,digest in hashes.items():self.assertEqual(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest(),digest)
        record=json.loads((HERE/'history/securities-summary-20261024.json').read_text(encoding='utf-8'))
        self.assertFalse(record['rdf_changed']);self.assertEqual(record['new_source_tables'],[])
        self.assertEqual(set(record['new_concepts']),SUMMARY_IDS)
        for r in record['source_evidence'].values():
            self.assertEqual(hashlib.sha256(source_path(r).read_bytes()).hexdigest(),r['sha256'])


if __name__=='__main__':unittest.main()
