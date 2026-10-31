// Read a metric's directly declared Customer dimension, without traversing totals.
// Customer property values are definitions, not actual customer identity values.
MATCH (m:PBConcept:PBConceptMetric {metricCode:$metricCode})
      -[:PB_MEASURES_CUSTOMER]->(c:PBConcept:PBConceptCustomer {conceptCode:'customer'})
RETURN m.metricCode AS metricCode, m.name AS metricName,
       c{.conceptCode,.name,.definition,.status,.customerId,.customerName,.customerNumber} AS customer
