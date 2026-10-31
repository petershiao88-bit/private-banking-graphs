import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, RDFS, SKOS, XSD

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ontology_builder", ROOT / "tools/build_ontology.py")
assert SPEC is not None and SPEC.loader is not None
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
FH = Namespace("https://example.org/ontology/holding#")
BANK = Namespace("https://example.org/ontology/bank#")


class OntologyTests(unittest.TestCase):
    def setUp(self):
        self.graph = Graph().parse(ROOT / "holding-core.ttl", format="turtle")

    def test_exact_common_classes_and_inheritance(self):
        expected = {FH[name] for name in ("Customer", "FinancialProduct", "ContactInformation",
                                         "MobileContactInformation", "AddressContactInformation",
                                         "Employee", "Metric", "FeeIncome", "AUM")}
        self.assertEqual(set(self.graph.subjects(RDF.type, OWL.Class)), expected)
        self.assertEqual(set(self.graph.subject_objects(RDFS.subClassOf)), {
            (FH.MobileContactInformation, FH.ContactInformation),
            (FH.AddressContactInformation, FH.ContactInformation),
            (FH.FeeIncome, FH.Metric),
            (FH.AUM, FH.Metric),
        })

    def test_shared_properties_domains_and_ranges(self):
        fields = {"mobileNumber": FH.MobileContactInformation, **{
            name: FH.AddressContactInformation for name in
            ("countryCode", "city", "district", "addressLine", "postalCode", "fullAddress")}}
        metric_fields = {
            "metricAmount": (FH.Metric, XSD.decimal),
            "aumAsOfDate": (FH.AUM, XSD.date),
            "valuationQuantity": (FH.AUM, XSD.decimal),
            "valuationUnitPrice": (FH.AUM, XSD.decimal),
            "incomePeriodStart": (FH.FeeIncome, XSD.date),
            "incomePeriodEnd": (FH.FeeIncome, XSD.date),
            "feeBaseAmount": (FH.FeeIncome, XSD.decimal),
            "feeDeductionAmount": (FH.FeeIncome, XSD.decimal),
        }
        self.assertEqual(set(self.graph.subjects(RDF.type, OWL.DatatypeProperty)),
                         {FH[name] for name in fields.keys() | metric_fields.keys()})
        for name, domain in fields.items():
            self.assertEqual(set(self.graph.objects(FH[name], RDFS.domain)), {domain})
            self.assertEqual(set(self.graph.objects(FH[name], RDFS.range)), {XSD.string})
        for name, (domain, datatype) in metric_fields.items():
            self.assertEqual(set(self.graph.objects(FH[name], RDFS.domain)), {domain})
            self.assertEqual(set(self.graph.objects(FH[name], RDFS.range)), {datatype})
        self.assertEqual(set(self.graph.subjects(RDF.type, OWL.ObjectProperty)),
                         {FH.holds, FH.hasContactPoint, FH.serves, FH.measuresProduct, FH.feeIncomeFromProduct})
        for prop, domain, target in ((FH.holds, FH.Customer, FH.FinancialProduct),
                                    (FH.hasContactPoint, FH.Customer, FH.ContactInformation),
                                    (FH.serves, FH.Employee, FH.Customer),
                                    (FH.measuresProduct, FH.AUM, FH.FinancialProduct),
                                    (FH.feeIncomeFromProduct, FH.FeeIncome, FH.FinancialProduct)):
            self.assertEqual(set(self.graph.objects(prop, RDFS.domain)), {domain})
            self.assertEqual(set(self.graph.objects(prop, RDFS.range)), {target})

    def test_no_company_or_department_terms_or_unapproved_axioms(self):
        for triple in self.graph:
            for term in triple:
                if isinstance(term, URIRef):
                    self.assertFalse(str(term).startswith(tuple(
                        "https://example.org/ontology/" + company
                        for company in ("bank", "securities", "life"))))
        forbidden = {OWL.sameAs, OWL.equivalentClass, OWL.equivalentProperty,
                     OWL.disjointWith, OWL.inverseOf, OWL.cardinality, OWL.minCardinality,
                     OWL.maxCardinality, OWL.hasKey, OWL.propertyChainAxiom}
        self.assertFalse(set(self.graph.predicates()) & forbidden)
        self.assertFalse(set(self.graph.subjects(RDF.type, OWL.NamedIndividual)))
        self.assertFalse(set(self.graph.subjects(RDF.type, OWL.FunctionalProperty)))
        self.assertFalse(set(self.graph.subjects(RDF.type, OWL.InverseFunctionalProperty)))
        self.assertNotIn(Literal("部門"), set(self.graph.objects(None, FH.governanceLevel)))

    def test_entities_have_concise_definitions_labels_and_governance(self):
        for kind in (OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty):
            for entity in self.graph.subjects(RDF.type, kind):
                self.assertTrue(list(self.graph.objects(entity, RDFS.label)))
                self.assertTrue(list(self.graph.objects(entity, SKOS.definition)))
                self.assertEqual(set(self.graph.objects(entity, FH.governanceLevel)), {Literal("金控")})

    def test_catalog_targets_exist_and_versions_match(self):
        import xml.etree.ElementTree as ET
        entries = {n.attrib["name"]: n.attrib["uri"]
                   for n in ET.parse(ROOT / "catalog-v001.xml").getroot()}
        for uri, path in entries.items():
            graph = Graph().parse(ROOT / path, format="turtle")
            self.assertTrue((URIRef(uri), RDF.type, OWL.Ontology) in graph
                            or (None, OWL.versionIRI, URIRef(uri)) in graph)
        self.assertEqual(len(entries), 12)

    def test_current_exports_match_source(self):
        report = builder.check_outputs(ROOT)
        self.assertEqual(report["classes"], 30)
        self.assertEqual(report["source_modules"], 5)
        self.assertEqual(report["object_properties"], 6)
        self.assertEqual(report["data_properties"], 16)
        self.assertEqual(report["annotation_properties"], 5)
        self.assertEqual(report["full_owl_reasoner"], "not run")

    def test_no_retired_modules_active(self):
        for name in ("bank-contact.ttl", "securities-contact.ttl", "life-contact.ttl",
                     "bank-business-contact.ttl"):
            self.assertFalse((ROOT / name).exists())
            self.assertTrue((ROOT / "archive/before-v0.3.0" / name).is_file())
        self.assertEqual(set(json.loads((ROOT / "build-config.json").read_text(encoding="utf-8"))["sources"]),
                         {"holding-core.ttl", "bank-deposit.ttl", "bank-common.ttl", "bank-investment-products.ttl", "securities-common.ttl"})

    def test_investment_product_categories_remain_independent_common_classes(self):
        graph = Graph().parse(ROOT / "bank-investment-products.ttl", format="turtle")
        expected = {BANK.StockProduct, BANK.BondProduct, BANK.FundProduct, BANK.OverseasFinancialProduct, BANK.InsuranceProduct, BANK.ETFProduct}
        self.assertEqual(set(graph.subjects(RDF.type, OWL.Class)), expected)
        for entity in expected:
            self.assertEqual(set(graph.objects(entity, RDFS.subClassOf)), {FH.FinancialProduct})
            self.assertEqual(set(graph.objects(entity, FH.governanceLevel)), {Literal("子公司")})
            self.assertEqual(set(graph.objects(entity, FH.subsidiary)), {Literal("銀行")})
            self.assertTrue(list(graph.objects(entity, RDFS.label)))
            self.assertTrue(list(graph.objects(entity, SKOS.definition)))
        self.assertFalse(set(graph.subjects(RDF.type, OWL.DatatypeProperty)))
        self.assertFalse(set(graph.subjects(RDF.type, OWL.ObjectProperty)))
        _, combined = builder.expected_graph(ROOT)
        for name in ("OverseasStockProduct", "OverseasBondProduct"):
            target = BANK[name]
            self.assertFalse(list(combined.triples((target, None, None))))
            self.assertFalse(list(combined.triples((None, None, target))))
        # Region does not establish currency, or make stock/bond disjoint by inference.
        for entity in expected:
            self.assertFalse(list(combined.objects(entity, OWL.equivalentClass)))
            self.assertFalse(list(combined.objects(entity, OWL.disjointWith)))
        previous = Graph()
        config = json.loads((ROOT / "archive/before-v0.6.0/build-config.json").read_text(encoding="utf-8"))
        for source in config["sources"]:
            previous.parse(ROOT / "archive/before-v0.6.0" / source, format="turtle")
        # All existing concept/property definitions survive the extension unchanged.
        for ontology in list(previous.subjects(RDF.type, OWL.Ontology)):
            previous.remove((ontology, None, None))
        preserved = Graph()
        subjects = set(previous.subjects())
        for triple in combined:
            if triple[0] in subjects:
                preserved.add(triple)
        # User-approved refinement: only AUM measures products; preserve every other old definition.
        for predicate in (RDFS.domain, SKOS.definition):
            previous.remove((FH.measuresProduct, predicate, None))
            preserved.remove((FH.measuresProduct, predicate, None))
        self.assertTrue(isomorphic(previous, preserved))

    def test_bank_common_classes_without_department_combinations(self):
        graph = Graph().parse(ROOT / "bank-deposit.ttl", format="turtle")
        parents = {
            "DepositProduct": {FH.FinancialProduct},
            "TWDFinancialProduct": {FH.FinancialProduct},
            "ForeignCurrencyFinancialProduct": {FH.FinancialProduct},
            "StructuredFinancialProduct": {FH.FinancialProduct},

        }
        self.assertEqual(set(graph.subjects(RDF.type, OWL.Class)), {BANK[name] for name in parents})
        self.assertEqual(set(graph.objects(None, OWL.imports)),
                         {URIRef("https://example.org/ontology/holding")})
        for name, expected in parents.items():
            self.assertEqual(set(graph.objects(BANK[name], RDFS.subClassOf)), expected)
            self.assertEqual(set(graph.objects(BANK[name], FH.governanceLevel)), {Literal("子公司")})
            self.assertEqual(set(graph.objects(BANK[name], FH.subsidiary)), {Literal("銀行")})
            self.assertTrue(list(graph.objects(BANK[name], RDFS.label)))
            self.assertTrue(list(graph.objects(BANK[name], SKOS.definition)))
        self.assertFalse(set(graph.subjects(RDF.type, OWL.DatatypeProperty)))
        self.assertFalse(set(graph.subjects(RDF.type, OWL.ObjectProperty)))

    def test_bank_insurance_is_a_broad_bank_product_without_policy_or_insurer_model(self):
        _, graph = builder.expected_graph(ROOT)
        self.assertEqual(set(graph.objects(BANK.InsuranceProduct, RDFS.subClassOf)), {FH.FinancialProduct})
        self.assertEqual(set(graph.objects(BANK.InsuranceProduct, FH.subsidiary)), {Literal("銀行")})
        self.assertEqual(set(graph.objects(BANK.InsuranceProduct, FH.governanceLevel)), {Literal("子公司")})
        definition = str(graph.value(BANK.InsuranceProduct, SKOS.definition))
        self.assertIn("銀行通路", definition)
        self.assertIn("範圍由部門描述", definition)
        for namespace in (FH, BANK, Namespace("https://example.org/ontology/life#")):
            for term in ("Policy", "InsuranceContract", "InvestmentLinkedInsuranceProduct"):
                self.assertNotIn(namespace[term], set(graph.subjects(RDF.type, OWL.Class)))
        self.assertFalse(set(graph.subjects(RDF.type, OWL.Restriction)))

    def test_no_unapproved_classes_constraints_or_product_balance(self):
        _, graph = builder.expected_graph(ROOT)
        classes = set(graph.subjects(RDF.type, OWL.Class))
        for name in ("FinancialProduct", "Employee", "EmployeeDepositProduct", "Account",
                     "BranchDepositProduct", "DigitalDepositProduct", "TWDDepositProduct",
                     "ForeignCurrencyDepositProduct", "StructuredDepositProduct"):
            self.assertNotIn(BANK[name], classes)
        for name in ("ProductFeeIncome", "FundFeeIncome"):
            self.assertNotIn(BANK[name], classes)
        forbidden = {OWL.sameAs, OWL.equivalentClass, OWL.equivalentProperty, OWL.disjointWith,
                     OWL.inverseOf, OWL.cardinality, OWL.minCardinality, OWL.maxCardinality,
                     OWL.hasKey, OWL.propertyChainAxiom, OWL.intersectionOf}
        self.assertFalse(set(graph.predicates()) & forbidden)
        for name in ("customerId", "currency", "balance", "snapshotDate"):
            self.assertNotIn(BANK[name], set(graph.subjects()))
        self.assertFalse(set(graph.objects(None, OWL.imports)))

    def test_core_semantics_unchanged_from_v030(self):
        before = Graph().parse(ROOT / "archive/before-v0.4.0/holding-core.ttl", format="turtle")
        current = Graph().parse(ROOT / "holding-core.ttl", format="turtle")
        header = URIRef("https://example.org/ontology/holding")
        before.remove((header, None, None))
        current.remove((header, None, None))
        # Existing common definitions remain identical while new subjects are added.
        old_subjects = set(before.subjects())
        preserved = Graph()
        for triple in current:
            if triple[0] in old_subjects:
                preserved.add(triple)
        self.assertTrue(isomorphic(before, preserved))

    def test_workforce_and_fee_hierarchies_are_separate_from_products(self):
        _, graph = builder.expected_graph(ROOT)
        for child, parent in ((BANK.BankEmployee, FH.Employee),
                              (BANK.BankFeeIncome, FH.FeeIncome), (FH.FeeIncome, FH.Metric)):
            self.assertEqual(set(graph.objects(child, RDFS.subClassOf)), {parent})
        self.assertEqual(set(graph.objects(BANK.employeeId, RDFS.domain)), {BANK.BankEmployee})
        self.assertEqual(set(graph.objects(BANK.employeeId, RDFS.range)), {XSD.string})
        for entity in (BANK.BankEmployee, BANK.BankFeeIncome, BANK.employeeId):
            self.assertEqual(set(graph.objects(entity, FH.governanceLevel)), {Literal("子公司")})
            self.assertEqual(set(graph.objects(entity, FH.subsidiary)), {Literal("銀行")})
            self.assertTrue(list(graph.objects(entity, SKOS.definition)))
        self.assertNotIn((BANK.BankFeeIncome, RDFS.subClassOf, FH.FinancialProduct), graph)
        self.assertFalse(set(graph.subjects(RDF.type, OWL.Restriction)))
        # Access classifications and role/product combinations remain unimplemented.
        for name in ("InternalMetric", "ExternalMetric"):
            self.assertNotIn(FH[name], set(graph.subjects()))

    def test_advisor_specializes_employee_and_receives_income_attribution(self):
        _, graph = builder.expected_graph(ROOT)
        self.assertEqual(set(graph.objects(BANK.FinancialAdvisor, RDFS.subClassOf)), {BANK.BankEmployee})
        self.assertEqual(set(graph.transitive_objects(BANK.FinancialAdvisor, RDFS.subClassOf)),
                         {BANK.FinancialAdvisor, BANK.BankEmployee, FH.Employee})
        prop = BANK.attributedToAdvisor
        self.assertIn((prop, RDF.type, OWL.ObjectProperty), graph)
        self.assertEqual(set(graph.objects(prop, RDFS.domain)), {BANK.BankFeeIncome})
        self.assertEqual(set(graph.objects(prop, RDFS.range)), {BANK.FinancialAdvisor})
        for entity in (BANK.FinancialAdvisor, prop):
            self.assertEqual(set(graph.objects(entity, FH.governanceLevel)), {Literal("子公司")})
            self.assertEqual(set(graph.objects(entity, FH.subsidiary)), {Literal("銀行")})
            self.assertTrue(list(graph.objects(entity, SKOS.definition)))
        # Advisor uses the existing employee ID; no allocation, uniqueness or temporal axiom is invented.
        self.assertEqual(set(graph.objects(BANK.employeeId, RDFS.domain)), {BANK.BankEmployee})
        self.assertNotIn(BANK.advisorId, set(graph.subjects()))
        self.assertNotIn((prop, RDF.type, OWL.FunctionalProperty), graph)
        self.assertFalse(set(graph.subjects(RDF.type, OWL.Restriction)))

    def test_aum_specializes_metric_and_owns_product_measurement(self):
        _, graph = builder.expected_graph(ROOT)
        self.assertEqual(set(graph.objects(BANK.BankAUM, RDFS.subClassOf)), {FH.AUM})
        self.assertEqual(set(graph.objects(FH.AUM, RDFS.subClassOf)), {FH.Metric})
        self.assertEqual(set(graph.objects(FH.measuresProduct, RDFS.domain)), {FH.AUM})
        self.assertEqual(set(graph.objects(FH.measuresProduct, RDFS.range)), {FH.FinancialProduct})
        self.assertEqual(set(graph.objects(FH.feeIncomeFromProduct, RDFS.domain)), {FH.FeeIncome})
        self.assertEqual(set(graph.objects(FH.feeIncomeFromProduct, RDFS.range)), {FH.FinancialProduct})
        # An income/product relation must not classify that income as AUM by its domain.
        self.assertNotIn(FH.AUM, set(graph.transitive_objects(BANK.BankFeeIncome, RDFS.subClassOf)))
        for prop in graph.subjects(RDF.type, OWL.ObjectProperty):
            self.assertFalse((prop, RDFS.domain, FH.Metric) in graph and
                             (prop, RDFS.range, FH.FinancialProduct) in graph)
        for name in ("StockAUM", "BondAUM", "TWDDepositAUM", "OverseasStockAUM"):
            self.assertNotIn(BANK[name], set(graph.subjects(RDF.type, OWL.Class)))

    def test_metric_elements_apply_to_both_subsidiaries_without_mixing_metric_domains(self):
        _, graph = builder.expected_graph(ROOT)
        sec = Namespace("https://example.org/ontology/securities#")
        for aum, fee in ((BANK.BankAUM, BANK.BankFeeIncome),
                         (sec.SecuritiesAUM, sec.SecuritiesFeeIncome)):
            aum_parents = set(graph.transitive_objects(aum, RDFS.subClassOf))
            fee_parents = set(graph.transitive_objects(fee, RDFS.subClassOf))
            self.assertIn(FH.Metric, aum_parents & fee_parents)
            for prop in (FH.aumAsOfDate, FH.valuationQuantity, FH.valuationUnitPrice):
                domain = graph.value(prop, RDFS.domain)
                self.assertIn(domain, aum_parents)
                self.assertNotIn(domain, fee_parents)
            for prop in (FH.incomePeriodStart, FH.incomePeriodEnd,
                         FH.feeBaseAmount, FH.feeDeductionAmount):
                domain = graph.value(prop, RDFS.domain)
                self.assertIn(domain, fee_parents)
                self.assertNotIn(domain, aum_parents)
        self.assertFalse(set(graph.subjects(RDF.type, OWL.Restriction)))
        self.assertFalse(set(graph.subjects(RDF.type, OWL.FunctionalProperty)))

    def test_forward_common_class_subclass_without_combination_inference(self):
        _, graph = builder.expected_graph(ROOT)
        pending = {BANK.TWDFinancialProduct}
        ancestors = set()
        while pending:
            item = pending.pop()
            if item not in ancestors:
                ancestors.add(item)
                pending.update(graph.objects(item, RDFS.subClassOf))
        self.assertEqual(ancestors, {BANK.TWDFinancialProduct, FH.FinancialProduct})
        for name in ("TWDDepositProduct", "ForeignCurrencyDepositProduct", "StructuredDepositProduct"):
            self.assertFalse(list(graph.triples((BANK[name], None, None))))
            self.assertFalse(list(graph.triples((None, None, BANK[name]))))
        # No equivalence/intersection axiom infers a subtype merely from two parent types.
        self.assertFalse(set(graph.subjects(OWL.equivalentClass, None)))
        self.assertFalse(set(graph.subjects(OWL.intersectionOf, None)))

    def test_build_is_source_driven_and_detects_stale_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("holding-core.ttl", "bank-deposit.ttl", "bank-common.ttl", "bank-investment-products.ttl", "securities-common.ttl", "build-config.json", "catalog-v001.xml"):
                shutil.copy2(ROOT / name, root / name)
            original_bytes = (root / "holding-core.ttl").read_bytes()
            builder.build(root)
            first = Graph().parse(root / "customer360-ontology.ttl", format="turtle")
            builder.build(root)
            self.assertTrue(isomorphic(first, Graph().parse(root / "customer360-ontology.ttl",
                                                           format="turtle")))
            self.assertEqual((root / "holding-core.ttl").read_bytes(), original_bytes)
            with (root / "holding-core.ttl").open("a", encoding="utf-8") as stream:
                stream.write('\nfh:Customer rdfs:comment "Test-only source change" .\n')
            with self.assertRaisesRegex(ValueError, "Stale"):
                builder.check_outputs(root)
            builder.build(root)
            self.assertIn((FH.Customer, RDFS.comment, Literal("Test-only source change")),
                          Graph().parse(root / "customer360-ontology.ttl", format="turtle"))

    def test_builder_rejects_unresolved_imports_and_source_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("holding-core.ttl", "bank-deposit.ttl", "bank-common.ttl", "bank-investment-products.ttl", "securities-common.ttl", "build-config.json", "catalog-v001.xml"):
                shutil.copy2(ROOT / name, root / name)
            with (root / "holding-core.ttl").open("a", encoding="utf-8") as stream:
                stream.write('\n<https://example.org/ontology/holding> owl:imports <urn:missing> .\n')
            with self.assertRaisesRegex(ValueError, "Import must"):
                builder.expected_graph(root)
            config = json.loads((root / "build-config.json").read_text(encoding="utf-8"))
            config["outputs"]["turtle"] = "holding-core.ttl"
            (root / "build-config.json").write_text(json.dumps(config), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                builder.expected_graph(root)
            with self.assertRaisesRegex(ValueError, "outside"):
                builder.local_file(root, "../outside.ttl")


if __name__ == "__main__":
    unittest.main()
