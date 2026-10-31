"""Test-only projection of the two approved income expansions onto older baselines.

Only names, definitions, source observations/table coverage and relation names
are normalized. Classes, fields, candidate evidence and relation semantics are
never ignored. The current expansion is checked directly in test_pg_income.py.
"""
import copy
import json
from pathlib import Path
from review_contract_v016 import historical_metric_concept, historical_metric_model

BASE = Path(__file__).resolve().parents[2] / 'archive/before-pg-income-extension-20261024/department-pg'
EXPANDED = {'bank.dci_fee_income': 'product-fees.json',
            'bank.insurance_fee_income': 'investment-metrics.json'}


def historical_income_concept(concept):
    result = historical_metric_concept(concept)
    if concept['id'] in EXPANDED:
        baseline = json.loads((BASE / EXPANDED[concept['id']]).read_text(encoding='utf-8'))
        old = next(c for c in baseline['concepts'] if c['id'] == concept['id'])
        for key in ('name', 'definition', 'observations', 'table_sources'):
            result[key] = copy.deepcopy(old[key])
    return result


def historical_income_model(model):
    result = historical_metric_model(model)
    ids = {c['id'] for c in result['concepts']}
    for cid, name in EXPANDED.items():
        if cid not in ids:
            continue
        baseline = json.loads((BASE / name).read_text(encoding='utf-8'))
        result['concepts'] = [historical_income_concept(c) for c in result['concepts']]
        old_relations = {r['id']: r for r in baseline['relation_definitions']}
        for r in result['relation_definitions']:
            if r['source_concept'] == cid:
                r['name'] = old_relations[r['id']]['name']
        added_evidence = ({'sql_dci_tmu', 'sql_dci_summary', 'fx_pnl'} if cid == 'bank.dci_fee_income'
                          else {'insurance_income_summary'})
        result['evidence'] = {k: v for k, v in result['evidence'].items() if k not in added_evidence}
        added_tables = ({'DSTAS.FO108_W'} if cid == 'bank.dci_fee_income'
                        else {'DSKPI.KPI_DET_IU_002_NEW', 'DSKPI.KPI_DET_OFI_001'})
        result['sources'] = [s for s in result['sources'] if s['table'] not in added_tables]
    return result
