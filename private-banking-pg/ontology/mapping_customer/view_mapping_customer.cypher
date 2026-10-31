// Direct product -> BusinessMetric -> mapping Customer. No PBConcept nodes.
MATCH customerPath=(metric:BusinessMetric)-[:MEASURES_CUSTOMER]->(customer:MappingCustomer {key:'pb_shared:customer:customer'})
OPTIONAL MATCH productPath=(product:SharedProduct {ontologyId:'pb_shared'})-[:MEASURED_BY_AUM|MEASURED_BY_INCOME|INCOME_DEFINITION_PENDING]->(metric)
RETURN customerPath,collect(DISTINCT productPath) AS productPaths
