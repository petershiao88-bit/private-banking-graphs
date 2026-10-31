// Business concept definitions only; no actual customer or personnel records.
MATCH (c:PBConcept:PBConceptCustomer {conceptCode:'customer'})
OPTIONAL MATCH (c)-[assignment:PB_ASSIGNED_TO]->(a:PBConcept:PBConceptAdvisor)
OPTIONAL MATCH (c)-[customerScope:PB_SCOPED_TO]->(customerOrg:PBConcept:PBConceptOrganization)
OPTIONAL MATCH (a)-[advisorScope:PB_SCOPED_TO]->(advisorOrg:PBConcept:PBConceptOrganization)
RETURN c{.conceptCode,.name,.definition,.businessRole,.customerId,.customerName,.customerNumber} AS customer,
 a{.conceptCode,.name,.definition,.roleResponsibilities,.serviceDescription,.advisorId,.advisorName,.employeeNumber} AS advisor,
 assignment{.definition,.businessConstraint} AS assignment,
 customerOrg{.conceptCode,.name,.definition,.aliases,.organizationType,.businessPurpose,.targetCustomer,.serviceScope} AS customerOrganization,
 customerScope{.definition,.businessConstraint} AS customerScope,
 advisorOrg{.conceptCode,.name,.definition,.aliases,.organizationType,.businessPurpose,.targetCustomer,.serviceScope} AS advisorOrganization,
 advisorScope{.definition,.businessConstraint} AS advisorScope
