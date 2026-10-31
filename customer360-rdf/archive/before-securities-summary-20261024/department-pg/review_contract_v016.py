"""Test-only normalization of the approved v0.16 display names and RDF additions.

Never normalize sources, subsidiary, ownership, fields, metric classes or rules.
The exact new names and additions are checked independently by department tests.
"""
import copy
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'archive/before-department-v0.16.0'


@lru_cache(maxsize=1)
def baseline_names():
    result = {}
    for name in ('advisory-income', 'product-fees', 'product-aum', 'investment-metrics', 'bank-business-metrics'):
        model = json.loads((BASE / 'department-pg' / (name + '.json')).read_text(encoding='utf-8'))
        for c in model['concepts']:
            if 'table_sources' in c:
                result[c['id']] = c['name']
    return result


def historical_metric_concept(concept):
    result = copy.deepcopy(concept)
    if result['id'] in baseline_names():
        result['name'] = baseline_names()[result['id']]
    return result


def historical_metric_model(model, version=None):
    result = copy.deepcopy(model)
    result['concepts'] = [historical_metric_concept(c) for c in result['concepts']]
    if version is not None:
        result['ontology_version'] = version
    return result


def pre_department_rdf(graph):
    from rdflib import URIRef
    from rdflib.namespace import OWL, RDF
    result = copy.deepcopy(graph)
    for subject in list(result.subjects(RDF.type, OWL.Ontology)):
        result.remove((subject, None, None))
    for uri in ('https://example.org/ontology/holding#Department',
                'https://example.org/ontology/holding#usesMetric',
                'https://example.org/ontology/bank#PrivateBankingDepartment'):
        result.remove((URIRef(uri), None, None))
    return result
