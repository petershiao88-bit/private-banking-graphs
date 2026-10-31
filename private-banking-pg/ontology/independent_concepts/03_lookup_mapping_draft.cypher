// Explicit MappingDraft binding; rules are evidence, never executable approval.
MATCH (p:MappingDraftProduct {key:$productKey,code:$productCode})
WHERE $domain IN ['aum','income'] AND p.key STARTS WITH 'draft:pb:20261012:product:'
MATCH (p)-[measure:MEASURED_BY_AUM|MEASURED_BY_INCOME]->(metric:MappingDraftMetric {key:$metricKey})
WHERE metric.key STARTS WITH 'draft:pb:20261012:metric:'
 AND type(measure)=CASE WHEN $domain='aum' THEN 'MEASURED_BY_AUM' ELSE 'MEASURED_BY_INCOME' END
MATCH (p)-[mapping:AUM_IMPLEMENTED_BY|INCOME_IMPLEMENTED_BY]->(source:MappingDraftTable)
WHERE type(mapping)=CASE WHEN $domain='aum' THEN 'AUM_IMPLEMENTED_BY' ELSE 'INCOME_IMPLEMENTED_BY' END
 AND mapping.mappingRole='base_source' AND source.tableRole='source'
 AND source.key STARTS WITH 'draft:pb:20261012:table:'
WITH p,measure,metric,mapping,source ORDER BY source.name
RETURN p.code AS productCode,p.name AS productName,$domain AS domain,
 'mapping_draft_rules' AS status,true AS mappingActive,false AS calculationAuthorized,
 collect({mappingFormat:'mapping_draft_rules',mappingType:type(mapping),mappingStatus:mapping.status,
   productScope:properties(measure),metricKey:metric.key,sourceTable:source.name,sourceKey:source.key,
   sourceMetadata:source.columns,calculationRules:mapping.calculationRules,queryRules:mapping.queryRules,
   dependencySourceTables:mapping.dependencySourceTables,externalPreconditions:mapping.externalPreconditions,
   reviewNotes:mapping.reviewNotes,identityJoinStatus:mapping.identityJoinStatus,
   calculationRuleReading:mapping.calculationRuleReading,calculationRulesVersion:mapping.calculationRulesVersion}) AS mappings
