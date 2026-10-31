"""Build the mapping-layer Customer extension from existing metadata only."""
import json
from pathlib import Path

import openpyxl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CUSTOMER_KEY = 'pb_shared:customer:customer'
ID_FIELDS = {'CUST_ID', 'CUSTOMER_ID', 'ORGCUST_KEY', 'CIF_ID', 'ENTITYNUMBER',
             'IDNO', 'ID', 'ID_NO', 'WKA28', 'YTRMRB025', 'WKB02'}
NAME_FIELDS = {'CUST_NAME', 'CNAME'}
NUMBER_FIELDS = {'CUST_NO'}


def build():
    concept = json.loads((HERE.parent / 'independent_concepts/concept_graph.json').read_text(encoding='utf-8'))
    customer = next(n['properties'] for n in concept['nodes'] if n['kind'] == 'customer')
    references = []
    for domain, filename in [('aum', 'AUM_metadata.xlsx'), ('income', '收入_metadata.xlsx')]:
        path = ROOT / 'sources/metadata' / filename
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for sheet in workbook.worksheets:
            for row_number, row in enumerate(sheet.values, 1):
                if len(row) < 5:
                    continue
                field = str(row[1] or '').strip().upper()
                attribute = 'customerId' if field in ID_FIELDS else 'customerName' if field in NAME_FIELDS else 'customerNumber' if field in NUMBER_FIELDS else None
                if not attribute:
                    continue
                description = str(row[4] or '')
                identifier_type = ('investor_account' if field == 'WKB02' else
                                   'legal_identifier' if any(word in description for word in ('身分證', '身份證', '統一編號', '統編', '身分證號')) else
                                   'source_customer_number' if attribute == 'customerNumber' else
                                   'source_customer_identifier' if attribute == 'customerId' else 'source_customer_name')
                references.append(dict(domain=domain, attribute=attribute,
                    file=str(path.relative_to(ROOT)).replace('\\', '/'), metadataSheet=sheet.title,
                    row=row_number, columnName=field, dataType=str(row[2] or ''),
                    definition=description, identifierType=identifier_type,
                    status='observed_in_metadata'))
        workbook.close()
    props = dict(key=CUSTOMER_KEY, ontologyId='pb_shared', code='customer', name='客戶',
                 definition='AUM與Income映射圖共用的客戶衡量對象；保存基本屬性定義與來源參考，不代表實際客戶資料或已完成的身分合併。',
                 status='model_confirmed', identityMappingStatus='pending_confirmation',
                 customerId=customer['customerId'], customerName=customer['customerName'],
                 customerNumber=customer['customerNumber'],
                 sourceAvailability='來源欄位存在於metadata，不保證現有彙整輸出保留名稱與編號；不得直接以同名識別碼串接來源。',
                 sourceMetadata=['sources/metadata/AUM_metadata.xlsx', 'sources/metadata/收入_metadata.xlsx'])
    for attribute in ('customerId', 'customerName', 'customerNumber'):
        props[attribute + 'Sources'] = [f"{r['file']}::{r['metadataSheet']}::{r['columnName']} | {r['definition']} | {r['identifierType']}"
                                        for r in references if r['attribute'] == attribute]
    external = []
    relationships = []
    for node in concept['nodes']:
        if node['kind'] not in ('aum', 'income'):
            continue
        key = node['kind'] + ':metric:' + node['properties']['metricCode']
        external.append(dict(key=key, label='BusinessMetric'))
        relationships.append(dict(source=key, target=CUSTOMER_KEY, type='MEASURES_CUSTOMER',
                                  properties=dict(ontologyId='pb_shared', origin='mapping_customer_v1',
                                                  status='model_confirmed', scope='customer',
                                                  note='指標直接指向客戶維度；不代表上層指標繼承或跨來源身分一致。')))
    for domain in ('aum', 'income'):
        key = domain + ':dimension:customer'
        external.append(dict(key=key, label='BusinessDimension'))
        relationships.append(dict(source=CUSTOMER_KEY, target=key, type='HAS_DOMAIN_DIMENSION',
                                  properties=dict(ontologyId='pb_shared', origin='mapping_customer_v1',
                                                  status='metadata_reference', domain=domain,
                                                  note='保留既有領域客戶維度；僅對照維度定義，不建立實際客戶身分合併。')))
    plan = dict(ontologyId='pb_shared', rootKey=CUSTOMER_KEY, version='mapping_customer_v1',
                nodes=[dict(key=CUSTOMER_KEY, labels=['BusinessDimension', 'MappingCustomer'], properties=props)],
                externalReferences=external, relationships=relationships)
    dictionary = dict(customer=props, sourceReferences=references,
                      customerIdentityUnresolved=True, customerRecordsCreated=False)
    for filename, document in [('graph_plan.json', plan), ('business_dictionary.json', dictionary)]:
        (HERE / filename).write_text(json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(newNodes=1, relationships=len(relationships), metricLinks=12,
                         domainDimensionLinks=2, metadataReferences=len(references))))


if __name__ == '__main__':
    build()
