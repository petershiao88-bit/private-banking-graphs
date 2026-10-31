"""Narrow annotation exceptions for historical RDF preservation tests.

Only labels/definitions explicitly revised by the reviewed v0.15 plan are normalized.
No type, inheritance, domain, range or other axiom is ignored.
"""
from rdflib import Namespace
from rdflib.namespace import RDFS, SKOS

FH = Namespace('https://example.org/ontology/holding#')
BANK = Namespace('https://example.org/ontology/bank#')
SEC = Namespace('https://example.org/ontology/securities#')
APPROVED_TEXT_CHANGES = {
    FH.metricAmount: {SKOS.definition},
    FH.FeeIncome: {RDFS.label, SKOS.definition},
    FH.feeIncomeFromProduct: {SKOS.definition},
    FH.incomePeriodStart: {SKOS.definition},
    FH.incomePeriodEnd: {SKOS.definition},
    FH.feeBaseAmount: {SKOS.definition},
    FH.feeDeductionAmount: {SKOS.definition},
    BANK.BankFeeIncome: {RDFS.label, SKOS.definition},
    BANK.attributedToAdvisor: {SKOS.definition},
    SEC.SecuritiesFeeIncome: {RDFS.label, SKOS.definition},
}


def normalize_reviewed_text(graph):
    for subject, predicates in APPROVED_TEXT_CHANGES.items():
        for predicate in predicates:
            graph.remove((subject, predicate, None))
    return graph
