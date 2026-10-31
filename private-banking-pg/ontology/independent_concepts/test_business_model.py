"""Offline behavior checks for legacy and business-v2 concept tooling."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from build_concepts import build
from concept_model import business_paths, product_catalog, project_graph, validate_plan, LABELS, key
from import_concepts import merge, preflight
from mapping_routes import build_routes

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
DRAFT=ROOT/'deliverables/concept_review/20261013/business_v2/business_concepts.proposed.json'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


class MemoryQueryCapture:
    def __init__(self,plan):
        self.plan=plan
        self.calls=[]
    def query(self,statement,parameters=None):
        self.calls.append((statement,parameters))
        if statement.startswith('CREATE CONSTRAINT') or 'MERGE (' in statement:
            return {'data':{'values':[]}}
        if 'any(l IN labels(n)' in statement:
            return {'data':{'values':[[key(n['properties']),LABELS[n['kind']],n['properties']] for n in self.plan['nodes']]}}
        if 'WHERE NOT x:PBConcept' in statement:
            return {'data':{'values':[[0]]}}
        if 'RETURN coalesce(a.productCode' in statement:
            return {'data':{'values':[[r['source'],r['type'],r['target'],r['properties']] for r in self.plan['relationships']]}}
        if 'UNWIND $routes AS route' in statement:
            return {'data':{'values':[[r['productCode'],r['domain'],1,1]+([1] if r['sourceGraph']=='mapping_draft_rules' else []) for r in parameters['routes']]}}
        raise AssertionError('Unexpected database interaction: '+statement)


class BusinessModelTests(unittest.TestCase):
    def setUp(self):
        self.legacy=read(ROOT/'deliverables/concept_build/20261013/baseline/concept_graph.json')
        raw=read(DRAFT)
        self.draft={k:copy.deepcopy(raw[k]) for k in ('nodes','relationships')}
        self.draft['importReady']=False
        self.shared=read(ROOT/'ontology/Shared_product_graph_plan.json')
        self.mapping=read(ROOT/'deliverables/mapping_review/20261012/integrated/base_tables/AUM_Income_底表映射計畫.json')

    def assert_invalid(self,plan):
        with self.assertRaises(RuntimeError):validate_plan(plan)

    def test_legacy_build_and_draft_are_separate(self):
        scratch=(ROOT/'.scratch').resolve()
        scratch.mkdir(exist_ok=True)
        tmpdir=tempfile.TemporaryDirectory(dir=scratch)
        self.assertTrue(Path(tmpdir.name).resolve().is_relative_to(ROOT.resolve()))
        with tmpdir as tmp:
            legacy=build(ROOT/'deliverables/concept_build/20261013/baseline/concept_graph.json',output=Path(tmp)/'legacy.json')
            draft=build(DRAFT,output=Path(tmp)/'draft.json')
            current=build(output=Path(tmp)/'current.json')
        self.assertEqual(legacy,self.legacy)
        self.assertEqual(current,read(HERE/'concept_graph.json'))
        self.assertFalse(draft['importReady'])
        self.assertEqual((len(draft['nodes']),len(draft['relationships'])),(41,69))
        with self.assertRaisesRegex(RuntimeError,'separate output'):build(DRAFT)

    def test_single_sided_offerings_and_context(self):
        self.assertEqual(len(business_paths(self.legacy)),29)
        paths=business_paths(self.draft)
        self.assertEqual(len(paths),39)
        catalog={p['productCode']:p for p in product_catalog(self.draft)}
        self.assertFalse(catalog['loan']['aumMetrics'])
        self.assertTrue(catalog['loan']['incomeMetrics'])
        self.assertFalse(catalog['deposit_twd']['incomeMetrics'])
        self.assertTrue(catalog['deposit_twd']['aumMetrics'])
        self.assertFalse(catalog['bank_collective_account']['incomeMetrics'])
        self.assertTrue(all('offeringType' not in product for product in catalog))
        self.assertTrue(all(not {'customer','advisor','private_banking'} & set(p['nodeKeys']) for p in paths))
        graph=project_graph(self.draft)
        self.assertTrue({'customer','advisor','private_banking'} <= {n['key'] for n in graph['nodes']})

    def test_unsupported_income_and_product_scope_rejected(self):
        plan=copy.deepcopy(self.draft)
        plan['relationships'].append({'source':'deposit_twd','type':'PB_INCOME_MEASURED_BY','target':'deposit_interest_income','properties':{'definition':'存款子類收入。'}})
        self.assert_invalid(plan)
        plan=copy.deepcopy(self.draft)
        plan['relationships'].append({'source':'bank_fund','type':'PB_SCOPED_TO','target':'private_banking','properties':{'definition':'產品指向組織。'}})
        self.assert_invalid(plan)
        plan=copy.deepcopy(self.draft)
        plan['relationships'].append({'source':'advisor','type':'PB_AUM_MEASURED_BY','target':'aum_total','properties':{'definition':'角色作為資產產品。'}})
        self.assert_invalid(plan)

    def test_cycles_cross_domain_duplicates_and_leaks_rejected(self):
        plan=copy.deepcopy(self.draft)
        plan['relationships'].append({'source':'aum_total','type':'PB_AUM_ROLLS_UP_TO','target':'aum_deposit','properties':{'definition':'逆向彙總。'}})
        self.assert_invalid(plan)
        plan=copy.deepcopy(self.draft)
        plan['relationships'][0]['target']='income_total'
        self.assert_invalid(plan)
        plan=copy.deepcopy(self.draft)
        plan['relationships'].append(copy.deepcopy(plan['relationships'][0]))
        self.assert_invalid(plan)
        plan=copy.deepcopy(self.draft)
        plan['nodes'][0]['properties']['queryRules']='SELECT * FROM hidden'
        self.assert_invalid(plan)
        plan=copy.deepcopy(self.draft)
        plan['relationships'][0]['properties']['sourceEvidence']='secret source'
        self.assert_invalid(plan)

    def test_bindings_have_evidence_and_do_not_invent_other_sides(self):
        routes=build_routes(self.draft,self.shared,self.mapping)
        self.assertEqual(len(routes),39)
        self.assertEqual(sum(r['sourceGraph']=='mapping_draft_rules' for r in routes),10)
        self.assertFalse(any(r['productCode']=='loan' and r['domain']=='aum' for r in routes))
        self.assertFalse(any(r['productCode']=='deposit_twd' and r['domain']=='income' for r in routes))
        broken=copy.deepcopy(self.mapping)
        broken['relationships']=[r for r in broken['relationships'] if not(r['from'].endswith('product:loan') and r['type']=='MEASURED_BY_INCOME')]
        with self.assertRaisesRegex(RuntimeError,'matching mapping evidence'):build_routes(self.draft,self.shared,broken)

    def test_general_import_still_refuses_changed_existing_content(self):
        self.draft['mappingRoutes']=build_routes(self.draft,self.shared,self.mapping)
        old=MemoryQueryCapture(self.legacy)
        with self.assertRaisesRegex(RuntimeError,'content differs'):preflight(old,old,self.draft)
        self.assertFalse(any('MERGE (' in q or 'CREATE CONSTRAINT' in q for q,_ in old.calls))
        exact=MemoryQueryCapture(self.draft)
        self.assertEqual(preflight(exact,exact,self.draft)['mappingRoutes'],39)

    def test_merge_uses_correct_role_endpoints_and_isolated_labels(self):
        db=MemoryQueryCapture(self.draft)
        merge(db,self.draft)
        writes=[(q,p) for q,p in db.calls if 'MERGE (' in q]
        self.assertEqual(len(writes),1)
        q,params=writes[0]
        self.assertIn('PBConceptAdvisor {conceptCode:edge.target}',q)
        self.assertIn('PBConceptOrganization {conceptCode:edge.target}',q)
        self.assertNotIn('MappingDraft',q)
        self.assertNotIn('SharedProduct',q)
        self.assertEqual(sum(len(v) for k,v in params.items() if k.startswith('edges')),69)
        self.assertEqual(sum(len(v) for k,v in params.items() if not k.startswith('edges')),41)
        self.assertTrue(all('offeringType' not in props for kind, values in params.items() if not kind.startswith('edges') for props in values))

    def test_validate_only_needs_no_credentials_and_draft_write_is_blocked(self):
        result=subprocess.run([sys.executable,'-X','utf8',str(HERE/'import_concepts.py'),'--validate-only','--plan',str(DRAFT)],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse(json.loads(result.stdout)['networkUsed'])
        result=subprocess.run([sys.executable,'-X','utf8',str(HERE/'import_concepts.py'),'--plan',str(DRAFT)],capture_output=True,text=True,encoding='utf-8')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Review draft is not an approved import plan',result.stderr)


if __name__=='__main__':
    unittest.main()
