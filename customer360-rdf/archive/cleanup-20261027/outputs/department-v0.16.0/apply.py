"""One-shot local migration from the confirmed pre-department snapshot."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
PG=ROOT/'department-pg'
BACKUP=ROOT/'archive/before-department-v0.16.0'
assert BACKUP.is_dir()
assert json.loads((ROOT/'build-config.json').read_text(encoding='utf-8'))['version']=='0.15.0'

def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

for filename in ('holding-core.ttl','bank-common.ttl','bank-deposit.ttl','bank-investment-products.ttl',
                 'securities-common.ttl','catalog-v001.xml'):
    p=ROOT/filename;p.write_text(p.read_text(encoding='utf-8').replace('0.15.0','0.16.0'),encoding='utf-8')
config=json.loads((ROOT/'build-config.json').read_text(encoding='utf-8'));config['version']='0.16.0'
write(ROOT/'build-config.json',config)
metric_ids=[]
name_changes={}
for name in ('model','deposits','advisory-income','product-fees','product-aum','investment-metrics','bank-business-metrics'):
    p=PG/(name+'.json');m=json.loads(p.read_text(encoding='utf-8'));m['ontology_version']='0.16.0'
    for c in m['concepts']:
        if 'table_sources' not in c:continue
        label={'bank':'銀行','securities':'證券'}[c['subsidiary']]
        old=c['name'];new='私銀－'+(old if old.startswith(label) else label+old)
        c['name']=new;metric_ids.append(c['id']);name_changes[c['id']]={'before':old,'after':new}
    write(p,m)
assert len(metric_ids)==len(set(metric_ids))==42
# Only active schemas/runtime checks and literal current-version expectations.
# Archive paths and all historical source files are left intact.
for p in list(PG.glob('*.py')):
    text=p.read_text(encoding='utf-8')
    text=text.replace('"0.15.0"','"0.16.0"').replace("'0.15.0'","'0.16.0'")
    if not p.name.startswith(('test_','review_')):
        text=text.replace('v0.15.0','v0.16.0').replace('ontology 0.15.0','ontology 0.16.0')
    p.write_text(text,encoding='utf-8')
p=PG/'model.schema.json';text=p.read_text(encoding='utf-8').replace('"0.15.0"','"0.16.0"');p.write_text(text,encoding='utf-8')

fh='https://example.org/ontology/holding#';bank='https://example.org/ontology/bank#'
dept={'schema_version':'1.0.0','ontology_version':'0.16.0','status':'active','scope':'metadata_only',
      'inference':False,'instance_mapping':False,'access_policy_status':'deferred_by_user',
      'department':{'id':'bank.private_banking','name':'私銀',
          'definition':'銀行私人銀行部門採用的業務指標範圍；本節點是 metadata 概念，不是已查驗的真實組織或權限實例。',
          'class_uri':bank+'PrivateBankingDepartment','subsidiary':'bank',
          'department_owner':None,'source_data_owner':None},
      'relation_definition':{'id':'bank.private_banking.uses_metric','name':'私銀採用指標',
          'property_uri':fh+'usesMetric','domain_uri':fh+'Department','range_uri':fh+'Metric'},
      'metric_ids':sorted(metric_ids)}
write(PG/'departments.json',dept)
write(PG/'history/department-v0.16.0.json',{'version':'0.16.0','date':'2026-10-24',
    'status':'implemented_locally_not_deployed','backup':'archive/before-department-v0.16.0',
    'new_rdf_classes':[fh+'Department',bank+'PrivateBankingDepartment'],
    'new_rdf_object_properties':[fh+'usesMetric'],'new_department_concept':'bank.private_banking',
    'metric_ids':sorted(metric_ids),'metric_name_changes':name_changes,
    'scope':'42 existing metrics adopted; no total metrics, source rules, field mapping or deployment',
    'source_data_owner':None})
print('v0.16.0: 42 stable metric IDs renamed; department metadata created')
