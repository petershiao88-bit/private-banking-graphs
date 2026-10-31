"""Department adoption is metadata, including the two reviewed securities summary scopes."""
import copy
import hashlib
import json
import unittest
from collections import Counter, deque
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS
from test_bank_business import builder
from review_contract_v016 import baseline_names, historical_metric_model, pre_department_rdf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BEFORE = ROOT / 'archive/before-department-v0.16.0'
FH = Namespace(builder.FH)
BANK = Namespace(builder.bank_business.BANK)
MODULES = (builder.advisory_income, builder.product_fees, builder.product_aum,
           builder.investment_metrics, builder.bank_business)


def metrics(include_summaries=True):
    result = {c['id']: c for module in MODULES for c in module.load_model()['concepts'] if 'table_sources' in c}
    if include_summaries:
        result.update({c['id']: c for c in builder.securities_summary.load_model()['concepts']})
    return result


class DepartmentTests(unittest.TestCase):
    def test_rdf_adds_exactly_two_classes_and_one_property_and_preserves_every_old_definition(self):
        old = Graph().parse(BEFORE/'customer360-ontology.ttl', format='turtle')
        now = Graph().parse(ROOT/'customer360-ontology.ttl', format='turtle')
        self.assertEqual(set(pre_department_rdf(old)), set(pre_department_rdf(now)))
        for g in (old, now):
            for subject in list(g.subjects(RDF.type, OWL.Ontology)): g.remove((subject,None,None))
        additions = set(now)-set(old)
        self.assertEqual(len(additions),16)
        self.assertEqual({t[0] for t in additions},{FH.Department,FH.usesMetric,BANK.PrivateBankingDepartment})
        self.assertEqual(set(now.objects(BANK.PrivateBankingDepartment,RDFS.subClassOf)),{FH.Department})
        self.assertEqual(set(now.objects(FH.usesMetric,RDFS.domain)),{FH.Department})
        self.assertEqual(set(now.objects(FH.usesMetric,RDFS.range)),{FH.Metric})
        self.assertIn((FH.department,RDF.type,OWL.AnnotationProperty),now)
        self.assertNotIn((FH.department,RDF.type,OWL.Class),now)
        self.assertFalse(set(now.subjects(RDF.type,OWL.NamedIndividual)))
        self.assertNotIn(FH.FinancialProduct,set(now.transitive_objects(BANK.PrivateBankingDepartment,RDFS.subClassOf)))

    def test_all_seven_existing_models_change_only_version_and_42_reviewed_names(self):
        actual = metrics(include_summaries=False)
        self.assertEqual(len(actual),42)
        self.assertEqual(set(actual),set(baseline_names()))
        for name in ('model','deposits','advisory-income','product-fees','product-aum','investment-metrics','bank-business-metrics'):
            old=json.loads((BEFORE/'department-pg'/(name+'.json')).read_text(encoding='utf-8'))
            current=json.loads((HERE/(name+'.json')).read_text(encoding='utf-8'))
            self.assertEqual(current['ontology_version'],'0.16.0')
            self.assertEqual(historical_metric_model(current,old['ontology_version']),old,name)
        for cid,c in actual.items():
            label={'bank':'銀行','securities':'證券'}[c['subsidiary']]
            original=baseline_names()[cid]
            self.assertEqual(c['name'],'私銀－'+(original if original.startswith(label) else label+original))

    def test_department_adopts_all_active_metric_kinds_and_preserves_source_subsidiaries(self):
        model=builder.departments.load_model()
        actual=metrics()
        self.assertEqual(set(model['metric_ids']),set(actual))
        self.assertEqual(Counter(c['subsidiary'] for c in actual.values()),{'bank':33,'securities':11})
        self.assertEqual(Counter(c['class_uri'].rsplit('#',1)[1] for c in actual.values()),{
            'BankAUM':13,'SecuritiesAUM':6,'BankFeeIncome':17,'SecuritiesFeeIncome':5,
            'BankLUM':1,'BankInterestIncome':2})
        graph=builder.build_combined_graph()
        nodes={n['id']:n for n in graph['nodes']}
        edges={(e['source'],e['type'],e['target']) for e in graph['relationships']}
        adopted={target for source,kind,target in edges if source=='bank.private_banking' and kind=='USES_METRIC'}
        self.assertEqual(adopted,set(actual))
        for cid,c in actual.items():
            p=nodes[cid]['properties']
            self.assertEqual(p['subsidiary'],c['subsidiary'])
            self.assertEqual(p['department_owner_json'],'null')
        for forbidden in ('bank.financial_advisor','bank.twd_deposit','bank.employee_deposit',
                          'bank.loan_verification_mobile','bank.collective_account_fee_income',
                          'securities.stock_pledge_lum','securities.stock_pledge_aum','securities.taiwan_stock_fee_income'):
            self.assertNotIn(forbidden,adopted)

    def test_type_references_adoption_semantics_and_source_paths_are_connected(self):
        graph=builder.build_combined_graph()
        nodes={n['id']:n for n in graph['nodes']}
        edges={(e['source'],e['type'],e['target']) for e in graph['relationships']}
        for edge in (
            ('bank.private_banking','REFERS_TO_CLASS',str(BANK.PrivateBankingDepartment)),
            (str(BANK.PrivateBankingDepartment),'HAS_PARENT_CLASS_REFERENCE',str(FH.Department)),
            ('bank.private_banking','HAS_RELATION_DEFINITION','bank.private_banking.uses_metric'),
            ('bank.private_banking.uses_metric','REFERS_TO_OBJECT_PROPERTY',str(FH.usesMetric)),
            (str(FH.usesMetric),'HAS_DOMAIN_CLASS',str(FH.Department)),
            (str(FH.usesMetric),'HAS_RANGE_CLASS',str(FH.Metric))): self.assertIn(edge,edges)
        neighbors={}
        for source,kind,target in edges:
            if kind in {'USES_METRIC','HAS_SOURCE_TABLE','USES_VALUATION_SOURCE','USES_DATE_LOOKUP_SOURCE'}:
                neighbors.setdefault(source,set()).add(target)
        found={'bank.private_banking'};queue=deque(found)
        while queue:
            for target in neighbors.get(queue.popleft(),set())-found:
                found.add(target);queue.append(target)
        self.assertEqual({nid for nid in found if nid.startswith('source:')},
                         {nid for nid,n in nodes.items() if n['label']=='SourceTable'})
        self.assertFalse(any(s=='bank.private_banking' and t.startswith('source:') for s,k,t in edges))
        self.assertFalse(any(s.startswith('securities.') and k=='HAS_RELATION_DEFINITION' and t.endswith('.advisor') for s,k,t in edges))
        self.assertEqual(nodes['bank.private_banking']['properties']['source_data_owner_json'],'null')

    def test_wrong_adoption_targets_duplicates_domains_ownership_and_execution_are_rejected(self):
        model=builder.departments.load_model()
        for change in ('missing','duplicate','product','pending','source','department','domain','range','property','ownership','sql','instances','permission'):
            m=copy.deepcopy(model)
            if change=='missing':m['metric_ids'].pop()
            elif change=='duplicate':m['metric_ids'][0]=m['metric_ids'][1]
            elif change in {'product','pending','source'}:
                m['metric_ids'][0]={'product':'bank.twd_deposit','pending':'securities.stock_pledge_lum','source':'source:DSDEP.DEP_FN_ACCT'}[change]
            elif change=='department':m['department']['id']='bank.private_banking_one'
            elif change=='domain':m['relation_definition']['domain_uri']=str(FH.Metric)
            elif change=='range':m['relation_definition']['range_uri']=str(FH.FinancialProduct)
            elif change=='property':m['relation_definition']['property_uri']=str(FH.measuresProduct)
            elif change=='ownership':m['department']['source_data_owner']='私人銀行'
            elif change=='sql':m['execution']={'sql':'SELECT 1'}
            elif change=='instances':m['instance_mapping']=True
            else:m['access_policy_status']='all_advisors_allowed'
            with self.subTest(change=change),self.assertRaises(ValueError):builder.render_combined_cypher(department_model=m)
        altered=metrics();altered['bank.fund_aum']['class_uri']=str(FH.FinancialProduct)
        with self.assertRaises(ValueError):builder.departments.build_graph(model,altered)

    def test_department_projection_is_deterministic_and_shared_metric_nodes_are_not_duplicated(self):
        model=builder.departments.load_model();model['metric_ids'].reverse()
        expected=builder.render_combined_cypher()
        self.assertEqual(expected,builder.render_combined_cypher(department_model=model))
        self.assertEqual(expected.encode('utf-8'),(HERE/'model.cypher').read_bytes())
        graph=builder.build_combined_graph()
        self.assertEqual(len(graph['nodes']),len({n['id'] for n in graph['nodes']}))
        self.assertEqual(len(graph['relationships']),len({e['id'] for e in graph['relationships']}))
        self.assertEqual(sum(n['label']=='SourceTable' for n in graph['nodes']),52)
        self.assertEqual(sum(n['label']=='DataFieldDefinition' for n in graph['nodes']),420)
        for e in graph['relationships']:
            if e['type']=='USES_METRIC':self.assertEqual(e['source'],'bank.private_banking')

    def test_source_hashes_pending_scope_and_history_ids_are_preserved(self):
        hashes=json.loads((BEFORE/'source-readonly-sha256.json').read_text(encoding='utf-8'))
        for relative,digest in hashes.items():self.assertEqual(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest(),digest)
        record=json.loads((HERE/'history/department-v0.16.0.json').read_text(encoding='utf-8'))
        self.assertEqual(set(record['metric_ids']),set(metrics(include_summaries=False)))
        self.assertEqual(set(record['metric_name_changes']),set(metrics(include_summaries=False)))
        for cid,c in metrics(include_summaries=False).items():
            self.assertEqual(record['metric_name_changes'][cid],{'before':baseline_names()[cid],'after':c['name']})
        for name in ('stock-pledge-aum-retired-v0.15.0.json','changes-v0.15.0.json',
                     'pg-income-extension-20261024.json','sql-scope-review-20261024.json'):
            self.assertEqual((HERE/'history'/name).read_bytes(),(BEFORE/'department-pg/history'/name).read_bytes())


if __name__=='__main__':unittest.main()
