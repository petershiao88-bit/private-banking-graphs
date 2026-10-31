// Product -> metric -> Customer; role and scope links provide business context.
MATCH path=(m:PBConcept:PBConceptMetric)-[:PB_HAS_MEASUREMENT_SUBJECT]->(c:PBConcept:PBConceptCustomer)
OPTIONAL MATCH productPath=(p:PBConcept:PBConceptProduct)-[:PB_AUM_MEASURED_BY|PB_INCOME_MEASURED_BY]->(m)
OPTIONAL MATCH advisorPath=(c)-[:PB_ASSIGNED_TO]->(:PBConcept:PBConceptAdvisor)
OPTIONAL MATCH customerScope=(c)-[:PB_SCOPED_TO]->(:PBConcept:PBConceptOrganization)
OPTIONAL MATCH advisorScope=(c)-[:PB_ASSIGNED_TO]->(:PBConcept:PBConceptAdvisor)-[:PB_SCOPED_TO]->(:PBConcept:PBConceptOrganization)
RETURN path, productPath, advisorPath, customerScope, advisorScope
