"""RDF 本體：FIBO 式模組結構、拆檔前後語意不變，以及沿用自 v0.16.0 的建模規則。"""

import json
from pathlib import Path
import sys
import unittest

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

from ontology_kit import build, versioning
from ontology_kit.config import Config

ROOT = Path(__file__).resolve().parents[2]
CFG = Config(ROOT / "config.yaml")
ARCHIVE = CFG.path_of("archive")
FH = Namespace("https://example.org/ontology/holding#")
BANK = Namespace("https://example.org/ontology/bank#")
SEC = Namespace("https://example.org/ontology/securities#")
sys.path.insert(0, str(ROOT / "tests/pg"))


def parse(*paths):
    graph = Graph()
    for path in paths:
        graph.parse(path, format="turtle")
    return graph


def layer(key):
    return parse(*[m.path for m in CFG.modules if m.layer == key])


def without_ontology_headers(graph):
    for subject in list(graph.subjects(RDF.type, OWL.Ontology)):
        graph.remove((subject, None, None))
    return graph


def combined():
    return build.expected_graph(CFG)


class ModuleStructureTests(unittest.TestCase):
    def test_module_layout_headers_and_maturity_follow_config(self):
        maturity = URIRef(CFG.annotations["maturity"])
        for m in CFG.modules:
            self.assertEqual(Path(m.file).parts[:2], ("ontology", m.layer), m.file)
            graph = parse(m.path)
            iri = URIRef(m.iri)
            self.assertIn((iri, RDF.type, OWL.Ontology), graph)
            self.assertEqual(set(graph.subjects(RDF.type, OWL.Ontology)), {iri}, "一個檔案只有一個 owl:Ontology")
            self.assertEqual(graph.value(iri, maturity), URIRef(CFG.maturity_levels[m.maturity]))
            self.assertTrue(any(l.language == "zh-TW" for l in graph.objects(iri, RDFS.label)))
            namespace = CFG.layers[m.layer].namespace
            for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty):
                for subject in graph.subjects(RDF.type, kind):
                    self.assertTrue(str(subject).startswith(namespace), f"{subject} 不屬於 {m.layer} 層")

    def test_split_preserves_every_v016_triple(self):
        current = without_ontology_headers(parse(*[m.path for m in CFG.modules]))
        v016 = without_ontology_headers(Graph().parse(CFG.release_dir("0.16.0") / "customer360-release.ttl"))
        self.assertTrue(isomorphic(current, v016))

    def test_each_subject_is_declared_in_exactly_one_module(self):
        owners = {}
        for m in CFG.modules:
            for subject in without_ontology_headers(parse(m.path)).subjects():
                self.assertIn(owners.setdefault(subject, m.file), (m.file,), f"{subject} 同時出現在多個模組")

    def test_imports_are_exactly_the_modules_whose_terms_are_used(self):
        declared = {}
        for m in CFG.modules:
            for subject in without_ontology_headers(parse(m.path)).subjects():
                declared[subject] = m.iri
        for m in CFG.modules:
            graph = parse(m.path)
            imports = {str(o) for o in graph.objects(URIRef(m.iri), OWL.imports)}
            used = {declared[t] for triple in without_ontology_headers(graph) for t in triple
                    if isinstance(t, URIRef) and t in declared} - {m.iri}
            self.assertEqual(imports, used, m.file)

    def test_catalog_targets_exist_and_versions_match(self):
        entries = versioning.catalog_entries(CFG)
        base = CFG.path_of("catalog").parent
        for name, target in entries.items():
            self.assertTrue((base / target).resolve().is_file(), target)
        self.assertEqual(len(entries), 2 * len(CFG.modules) + 2)
        self.assertEqual(versioning.check(CFG), [])

    def test_build_output_matches_sources(self):
        self.assertEqual(build.check(CFG)["result"], "PASS")

    def test_no_retired_modules_active(self):
        for name in ("bank-contact.ttl", "securities-contact.ttl", "life-contact.ttl", "bank-business-contact.ttl"):
            self.assertTrue((ARCHIVE / "before-v0.3.0" / name).is_file())
            self.assertFalse(any(Path(m.file).name == name for m in CFG.modules))


class HoldingLayerTests(unittest.TestCase):
    def setUp(self):
        self.graph = layer("holding")

    def test_exact_common_classes_and_inheritance(self):
        expected = {FH[name] for name in ("Customer", "FinancialProduct", "ContactInformation",
                                         "MobileContactInformation", "AddressContactInformation",
                                         "Employee", "Metric", "FeeIncome", "AUM", "LUM", "InterestIncome", "Department")}
        self.assertEqual(set(self.graph.subjects(RDF.type, OWL.Class)), expected)
        self.assertEqual(set(self.graph.subject_objects(RDFS.subClassOf)), {
            (FH.MobileContactInformation, FH.ContactInformation), (FH.AddressContactInformation, FH.ContactInformation),
            (FH.FeeIncome, FH.Metric), (FH.AUM, FH.Metric), (FH.LUM, FH.Metric), (FH.InterestIncome, FH.Metric)})

    def test_customer_holds_financial_product_and_other_shared_relations(self):
        for prop, domain, target in ((FH.holds, FH.Customer, FH.FinancialProduct),
                                     (FH.hasContactPoint, FH.Customer, FH.ContactInformation),
                                     (FH.serves, FH.Employee, FH.Customer),
                                     (FH.measuresProduct, FH.AUM, FH.FinancialProduct),
                                     (FH.feeIncomeFromProduct, FH.FeeIncome, FH.FinancialProduct),
                                     (FH.lumMeasuresProduct, FH.LUM, FH.FinancialProduct),
                                     (FH.interestIncomeFromProduct, FH.InterestIncome, FH.FinancialProduct),
                                     (FH.usesMetric, FH.Department, FH.Metric)):
            self.assertEqual(set(self.graph.objects(prop, RDFS.domain)), {domain})
            self.assertEqual(set(self.graph.objects(prop, RDFS.range)), {target})
        self.assertEqual(set(self.graph.subjects(RDF.type, OWL.ObjectProperty)),
                         {FH.holds, FH.hasContactPoint, FH.serves, FH.measuresProduct, FH.feeIncomeFromProduct,
                          FH.lumMeasuresProduct, FH.interestIncomeFromProduct, FH.usesMetric})
        products = parse(CFG.root / "ontology/holding/products.ttl")
        self.assertIn((FH.holds, RDF.type, OWL.ObjectProperty), products, "持有關係放在金融商品模組")

    def test_shared_data_properties(self):
        fields = {"mobileNumber": FH.MobileContactInformation, **{
            name: FH.AddressContactInformation for name in
            ("countryCode", "city", "district", "addressLine", "postalCode", "fullAddress")}}
        metric_fields = {
            "metricAmount": (FH.Metric, XSD.decimal), "lumAsOfDate": (FH.LUM, XSD.date),
            "interestPeriodStart": (FH.InterestIncome, XSD.date), "interestPeriodEnd": (FH.InterestIncome, XSD.date),
            "aumAsOfDate": (FH.AUM, XSD.date), "valuationQuantity": (FH.AUM, XSD.decimal),
            "valuationUnitPrice": (FH.AUM, XSD.decimal), "incomePeriodStart": (FH.FeeIncome, XSD.date),
            "incomePeriodEnd": (FH.FeeIncome, XSD.date), "feeBaseAmount": (FH.FeeIncome, XSD.decimal),
            "feeDeductionAmount": (FH.FeeIncome, XSD.decimal)}
        self.assertEqual(set(self.graph.subjects(RDF.type, OWL.DatatypeProperty)),
                         {FH[name] for name in fields.keys() | metric_fields.keys()})
        for name, domain in fields.items():
            self.assertEqual(set(self.graph.objects(FH[name], RDFS.domain)), {domain})
            self.assertEqual(set(self.graph.objects(FH[name], RDFS.range)), {XSD.string})
        for name, (domain, datatype) in metric_fields.items():
            self.assertEqual(set(self.graph.objects(FH[name], RDFS.domain)), {domain})
            self.assertEqual(set(self.graph.objects(FH[name], RDFS.range)), {datatype})

    def test_no_company_terms_or_unapproved_axioms(self):
        for triple in without_ontology_headers(self.graph):
            for term in triple:
                if isinstance(term, URIRef):
                    self.assertFalse(str(term).startswith(tuple(
                        "https://example.org/ontology/" + company for company in ("bank", "securities", "life"))))
        forbidden = {OWL.sameAs, OWL.equivalentClass, OWL.equivalentProperty, OWL.disjointWith, OWL.inverseOf,
                     OWL.cardinality, OWL.minCardinality, OWL.maxCardinality, OWL.hasKey, OWL.propertyChainAxiom}
        self.assertFalse(set(self.graph.predicates()) & forbidden)
        self.assertFalse(set(self.graph.subjects(RDF.type, OWL.NamedIndividual)))
        self.assertFalse(set(self.graph.subjects(RDF.type, OWL.FunctionalProperty)))
        self.assertNotIn(Literal("部門"), set(self.graph.objects(None, FH.governanceLevel)))

    def test_entities_have_labels_definitions_and_governance(self):
        for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty):
            for entity in self.graph.subjects(RDF.type, kind):
                self.assertTrue(list(self.graph.objects(entity, RDFS.label)))
                self.assertTrue(list(self.graph.objects(entity, SKOS.definition)))
                self.assertEqual(set(self.graph.objects(entity, FH.governanceLevel)), {Literal("金控")})

    def test_core_semantics_unchanged_from_v030(self):
        before = without_ontology_headers(Graph().parse(ARCHIVE / "before-v0.4.0/holding-core.ttl", format="turtle"))
        current = without_ontology_headers(self.graph)
        old_subjects = set(before.subjects())
        preserved = Graph()
        for triple in current:
            if triple[0] in old_subjects:
                preserved.add(triple)
        self.assertTrue(isomorphic(before, preserved))


class SubsidiaryLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = combined()

    def test_bank_products_are_independent_common_classes(self):
        products = parse(CFG.root / "ontology/bank/products.ttl")
        expected = {BANK[n] for n in ("StockProduct", "BondProduct", "FundProduct", "OverseasFinancialProduct",
                                      "InsuranceProduct", "ETFProduct", "CollectiveManagementProduct", "GoldProduct",
                                      "LoanProduct", "PlannedTrustProduct", "TrustCustodyProduct",
                                      "ForeignExchangeProduct", "LetterOfCreditProduct", "DepositProduct",
                                      "TWDFinancialProduct", "ForeignCurrencyFinancialProduct",
                                      "StructuredFinancialProduct")}
        self.assertEqual(set(products.subjects(RDF.type, OWL.Class)), expected)
        for entity in expected:
            self.assertEqual(set(products.objects(entity, RDFS.subClassOf)), {FH.FinancialProduct})
            self.assertEqual(set(products.objects(entity, FH.governanceLevel)), {Literal("子公司")})
            self.assertEqual(set(products.objects(entity, FH.subsidiary)), {Literal("銀行")})
            self.assertTrue(list(products.objects(entity, SKOS.definition)))
        self.assertFalse(set(products.subjects(RDF.type, OWL.DatatypeProperty)))
        self.assertFalse(set(products.subjects(RDF.type, OWL.ObjectProperty)))
        for name in ("OverseasStockProduct", "OverseasBondProduct", "TWDDepositProduct",
                     "ForeignCurrencyDepositProduct", "StructuredDepositProduct"):
            self.assertFalse(list(self.graph.triples((BANK[name], None, None))))
            self.assertFalse(list(self.graph.triples((None, None, BANK[name]))))

    def test_v06_definitions_survive_later_extensions(self):
        from review_contract_v015 import normalize_reviewed_text
        config = json.loads((ARCHIVE / "before-v0.6.0/build-config.json").read_text(encoding="utf-8"))
        previous = without_ontology_headers(parse(*[ARCHIVE / "before-v0.6.0" / s for s in config["sources"]]))
        subjects = set(previous.subjects())
        preserved = Graph()
        for triple in self.graph:
            if triple[0] in subjects:
                preserved.add(triple)
        for predicate in (RDFS.domain, SKOS.definition):  # 已核定：只有 AUM 衡量商品
            previous.remove((FH.measuresProduct, predicate, None))
            preserved.remove((FH.measuresProduct, predicate, None))
        self.assertTrue(isomorphic(normalize_reviewed_text(previous), normalize_reviewed_text(preserved)))

    def test_bank_insurance_is_a_broad_bank_product(self):
        g = self.graph
        self.assertEqual(set(g.objects(BANK.InsuranceProduct, RDFS.subClassOf)), {FH.FinancialProduct})
        definition = str(g.value(BANK.InsuranceProduct, SKOS.definition))
        self.assertIn("銀行通路", definition)
        self.assertIn("範圍由部門描述", definition)
        for namespace in (FH, BANK, Namespace("https://example.org/ontology/life#")):
            for term in ("Policy", "InsuranceContract", "InvestmentLinkedInsuranceProduct"):
                self.assertNotIn(namespace[term], set(g.subjects(RDF.type, OWL.Class)))

    def test_no_unapproved_classes_constraints_or_imports_in_build(self):
        g = self.graph
        classes = set(g.subjects(RDF.type, OWL.Class))
        for name in ("FinancialProduct", "Employee", "EmployeeDepositProduct", "Account", "BranchDepositProduct",
                     "DigitalDepositProduct", "ProductFeeIncome", "FundFeeIncome"):
            self.assertNotIn(BANK[name], classes)
        forbidden = {OWL.sameAs, OWL.equivalentClass, OWL.equivalentProperty, OWL.disjointWith, OWL.inverseOf,
                     OWL.cardinality, OWL.minCardinality, OWL.maxCardinality, OWL.hasKey, OWL.propertyChainAxiom,
                     OWL.intersectionOf}
        self.assertFalse(set(g.predicates()) & forbidden)
        self.assertFalse(set(g.subjects(RDF.type, OWL.Restriction)))
        self.assertFalse(set(g.objects(None, OWL.imports)), "合併產物不保留模組間 import")

    def test_workforce_advisor_and_fee_hierarchies(self):
        g = self.graph
        for child, parent in ((BANK.BankEmployee, FH.Employee), (BANK.FinancialAdvisor, BANK.BankEmployee),
                              (BANK.BankFeeIncome, FH.FeeIncome), (FH.FeeIncome, FH.Metric)):
            self.assertEqual(set(g.objects(child, RDFS.subClassOf)), {parent})
        self.assertEqual(set(g.objects(BANK.employeeId, RDFS.domain)), {BANK.BankEmployee})
        self.assertEqual(set(g.objects(BANK.attributedToAdvisor, RDFS.domain)), {BANK.BankFeeIncome})
        self.assertEqual(set(g.objects(BANK.attributedToAdvisor, RDFS.range)), {BANK.FinancialAdvisor})
        self.assertNotIn((BANK.BankFeeIncome, RDFS.subClassOf, FH.FinancialProduct), g)
        self.assertNotIn(BANK.advisorId, set(g.subjects()))
        for name in ("InternalMetric", "ExternalMetric"):
            self.assertNotIn(FH[name], set(g.subjects()))

    def test_metric_elements_apply_to_both_subsidiaries_without_mixing_domains(self):
        g = self.graph
        for aum, fee in ((BANK.BankAUM, BANK.BankFeeIncome), (SEC.SecuritiesAUM, SEC.SecuritiesFeeIncome)):
            aum_parents = set(g.transitive_objects(aum, RDFS.subClassOf))
            fee_parents = set(g.transitive_objects(fee, RDFS.subClassOf))
            self.assertIn(FH.Metric, aum_parents & fee_parents)
            for prop in (FH.aumAsOfDate, FH.valuationQuantity, FH.valuationUnitPrice):
                self.assertIn(g.value(prop, RDFS.domain), aum_parents - fee_parents)
            for prop in (FH.incomePeriodStart, FH.incomePeriodEnd, FH.feeBaseAmount, FH.feeDeductionAmount):
                self.assertIn(g.value(prop, RDFS.domain), fee_parents - aum_parents)
        self.assertNotIn(FH.AUM, set(g.transitive_objects(BANK.BankFeeIncome, RDFS.subClassOf)))

    def test_product_classes_do_not_infer_combinations(self):
        g = self.graph
        self.assertEqual(set(g.transitive_objects(BANK.TWDFinancialProduct, RDFS.subClassOf)),
                         {BANK.TWDFinancialProduct, FH.FinancialProduct})
        self.assertFalse(set(g.subjects(OWL.equivalentClass, None)))
        self.assertFalse(set(g.subjects(OWL.intersectionOf, None)))


if __name__ == "__main__":
    unittest.main()
