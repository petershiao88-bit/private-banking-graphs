"""Verify cross-company semantics, source conflicts and safe offline expansion."""
import copy
import importlib.util
import json
import re
import unittest
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS
from test_product_fees import source_path, workbook_cells

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent


def module_at(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder=module_at('investment_builder_tests',HERE/'build_cypher.py')
investment=builder.investment_metrics


class InvestmentMetricTests(unittest.TestCase):
    def setUp(self):
        self.model=investment.load_model()
        self.concepts={c['id']:c for c in self.model['concepts']}

    def test_company_classes_inherit_holding_and_preserve_previous_semantics(self):
        graph=Graph().parse(ROOT/'customer360-ontology.ttl',format='turtle')
        fh,bank,sec=map(Namespace,(investment.FH,investment.BANK,investment.SEC))
        parents={sec.SecuritiesAUM:fh.AUM,sec.SecuritiesFeeIncome:fh.FeeIncome,
                 **{sec[p]:fh.FinancialProduct for p in ('StockProduct','BondProduct','FundProduct',
                                                        'StructuredFinancialProduct','OverseasFinancialProduct')},
                 bank.FundProduct:fh.FinancialProduct}
        for child,parent in parents.items():
            self.assertEqual(set(graph.objects(child,RDFS.subClassOf)),{parent})
            company='銀行' if child==bank.FundProduct else '證券'
            self.assertEqual(set(graph.objects(child,fh.subsidiary)),{Literal(company)})
            self.assertTrue(list(graph.objects(child,SKOS.definition)))
            self.assertNotIn(bank.BankAUM,set(graph.transitive_objects(child,RDFS.subClassOf)))
        self.assertEqual(set(graph.objects(fh.feeIncomeFromProduct,RDFS.domain)),{fh.FeeIncome})
        self.assertEqual(set(graph.objects(fh.feeIncomeFromProduct,RDFS.range)),{fh.FinancialProduct})
        previous=Graph().parse(ROOT/'archive/before-v0.10.0/customer360-ontology.ttl',format='turtle')
        for ontology in list(previous.subjects(RDF.type,OWL.Ontology)):
            previous.remove((ontology,None,None))
        preserved={t for t in graph if t[0] in set(previous.subjects())}
        self.assertEqual(set(previous),preserved)

    def test_metric_product_relations_and_subsidiary_ownership_survive_projection(self):
        graph=investment.build_graph(self.model)
        nodes={n['id']:n for n in graph['nodes']}
        for cid,c in self.concepts.items():
            self.assertEqual(nodes[cid]['properties']['subsidiary'],c['subsidiary'])
            targets={e['target'] for e in graph['relationships']
                     if e['source']==cid+'.product' and e['type']=='HAS_TARGET_CLASS'}
            self.assertEqual(targets,{investment.FH+'FinancialProduct',*c['product_class_uris']})
            metric='AUM' if cid.endswith('_aum') else 'FeeIncome'
            r=next(r for r in self.model['relation_definitions'] if r['id']==cid+'.product')
            self.assertEqual(r['domain_uri'],investment.FH+metric)
            self.assertEqual(r['property_uri'],investment.FH+('measuresProduct' if metric=='AUM' else 'feeIncomeFromProduct'))
        advisor=[r for r in self.model['relation_definitions'] if r['id'].endswith('.advisor')]
        self.assertEqual([r['source_concept'] for r in advisor],['bank.fund_fee_income'])
        self.assertFalse(any(c['id']=='securities.taiwan_stock_fee_income' for c in self.model['concepts']))

    def test_input_candidates_and_exact_metadata_cells_are_supported_by_source_files(self):
        evidence=self.model['evidence']
        workbooks={}
        for eid,record in evidence.items():
            if 'cells' in record:
                cells=workbooks.setdefault((record['file'],record['sheet']),workbook_cells(source_path(record),record['sheet']))
                for address,value in record['cells'].items():
                    self.assertEqual(cells[address],value,(eid,address))
        for c in self.model['concepts']:
            for f in c['fields']:
                for candidate in f['candidates']:
                    supported=False
                    for eid in candidate['evidence']:
                        record=evidence[eid]
                        if 'lines' in record:
                            lines=source_path(record).read_text(encoding=record['encoding']).splitlines()
                            start,end=record['lines'];text='\n'.join(lines[start-1:end]).upper()
                            supported |= candidate['table'] in text and re.search(
                                r'\b'+re.escape(candidate['column'].upper())+r'\b',text) is not None
                        elif 'sheet' in record:
                            cells=workbooks.setdefault((record['file'],record['sheet']),workbook_cells(source_path(record),record['sheet']))
                            supported |= record['sheet']==candidate['table'] and candidate['column'].upper() in {
                                str(v).upper() for v in cells.values()}
                    self.assertTrue(supported,(c['id'],f['field'],candidate))
        products=json.loads(source_path(evidence['private_products']).read_text(encoding='utf-8'))
        codes=set()
        def collect(value):
            if isinstance(value,dict):
                if 'productCode' in value and 'definition' in value: codes.add(value['productCode'])
                for item in value.values():collect(item)
            elif isinstance(value,list):
                for item in value:collect(item)
        collect(products)
        self.assertTrue({c['product_code'] for c in self.model['concepts']}<=codes)

    def test_conflicting_customer_roles_net_fee_and_month_markers_remain_unresolved(self):
        fund=self.concepts['securities.fund_aum']
        identity=next(f for f in fund['fields'] if f['field']=='customerId')
        self.assertEqual({c['column'] for c in identity['candidates']},{'WKB02','WKB24'})
        self.assertIn('投資人帳號',fund['observations']['gaps'][0])
        stock=self.concepts['securities.foreign_stock_fee_income']
        self.assertIn('(CFEE - ABFEE) * FXRATE',stock['observations']['valuation_observation'])
        self.assertIn('不是快照日',stock['observations']['date_observation'])
        amount=next(f for f in stock['fields'] if f['field']=='amount')
        self.assertNotIn('DSPBM.PB_STOCKTRADM_AM_SEC',{c['table'] for c in amount['candidates']})
        source_text=source_path(self.model['evidence']['sec_stock_fee']).read_text(encoding='cp950').upper()
        self.assertIn('SUM((CFEE-ABFEE)*FXRATE)',source_text)
        self.assertIn('FROM DSPBM.PB_STOCKTRADM_AM_SEC_M',source_text)
        self.assertIn('MAX(YYYYMMDD) FROM DSPBM.PB_STOCKTRADM_AM_SEC@',source_text)
        for c in self.model['concepts']:
            for f in c['fields']:
                self.assertIsNone(f['table']);self.assertIsNone(f['column'])
                if c['metric_kind']=='fee_income' and f['field']=='snapshotDate':self.assertEqual(f['candidates'],[])
        self.assertTrue(all(v is None for v in self.model['execution'].values()))
        self.assertEqual(self.model['access_policy_status'],'deferred_by_user')

    def test_rejects_early_mapping_wrong_domains_and_lost_estimation_inputs(self):
        changes=[]
        for key in self.model['execution']:
            changed=copy.deepcopy(self.model);changed['execution'][key]='unapproved';changes.append(changed)
        changed=copy.deepcopy(self.model);changed['concepts'][0]['fields'][0]['table']='DSFND.PB_FUND_MONTH';changes.append(changed)
        changed=copy.deepcopy(self.model);changed['relation_definitions'][0]['domain_uri']=investment.FH+'Metric';changes.append(changed)
        changed=copy.deepcopy(self.model);changed['concepts'][2]['class_uri']=investment.BANK+'BankAUM';changes.append(changed)
        changed=copy.deepcopy(self.model)
        stock=next(c for c in changed['concepts'] if c['id']=='securities.foreign_stock_fee_income')
        field=next(f for f in stock['fields'] if f['field']=='amount');field['candidates']=[v for v in field['candidates'] if v['column']!='ABFEE'];changes.append(changed)
        for i,changed in enumerate(changes):
            with self.subTest(change=i),self.assertRaises(ValueError):
                builder.render_combined_cypher(investment_model=changed)

    def test_reordering_is_deterministic_and_previous_pg_nodes_and_edges_survive(self):
        changed=copy.deepcopy(self.model)
        for key in ('concepts','sources','relation_definitions','pending_scope'):changed[key].reverse()
        for source in changed['sources']:source['evidence'].reverse()
        for record in changed['evidence'].values():
            if 'rows' in record:record['rows'].reverse()
        for item in changed['pending_scope']:item['evidence'].reverse()
        for c in changed['concepts']:
            c['fields'].reverse();c['product_class_uris'].reverse();c['observations']['evidence'].reverse()
            for f in c['fields']:
                f['candidates'].reverse()
                for v in f['candidates']:v['evidence'].reverse()
        output=builder.render_combined_cypher()
        self.assertEqual(output,builder.render_combined_cypher(investment_model=changed))
        self.assertEqual(output.encode('utf-8'),(HERE/'model.cypher').read_bytes())
        old=module_at('previous_pg_v090',ROOT/'archive/before-v0.10.0/department-pg/build_cypher.py').build_combined_graph()
        current=builder.build_combined_graph()
        nodes={n['id']:n for n in current['nodes']}
        edges={e['id']:e for e in current['relationships']}
        for n in old['nodes']:
            if n['label']=='MetadataModule':n['properties']['ontology_version']='0.10.0'
            current_node=copy.deepcopy(nodes[n['id']])
            if current_node['label']=='BusinessConcept':
                current_node['properties'].pop('table_sources_json',None)
            if current_node['id']=='department-pg.advisory-income':
                current_node['properties'].pop('evidence_json',None)
            self.assertEqual(n,current_node)
        for e in old['relationships']:self.assertEqual(e,edges[e['id']])


if __name__=='__main__':unittest.main()
