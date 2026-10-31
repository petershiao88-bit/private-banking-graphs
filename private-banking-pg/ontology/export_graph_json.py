"""Package a full read-only Aura Query JSON download for offline graph use."""
import argparse
import hashlib
import json
import shutil
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'draft:pb:20261012:'
EXCLUDED = {PREFIX + 'metric:' + c for c in
            ('income', 'report_income_amount', 'report_row_count')}
CONCEPT_TYPES = {'MEASURED_BY_AUM', 'MEASURED_BY_INCOME', 'AUM_ROLLS_UP_TO',
                 'INCOME_ROLLS_UP_TO', 'MEASURES', 'SCOPED_TO', 'SUBCATEGORY_OF',
                 'INCOME_DEFINITION_PENDING', 'ASSIGNED_TO'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def normalize(raw):
    assert len({n['id'] for n in raw['nodes']}) == len(raw['nodes'])
    nodes = []
    for n in raw['nodes']:
        p = n['properties']
        code = next((p[k] for k in ('productCode', 'metricCode', 'conceptCode') if p.get(k)), None)
        key = ('pbconcept:' + code) if 'PBConcept' in n['labels'] else p.get('key')
        assert key, f"Missing stable node key: {n['id']}"
        nodes.append(dict(key=key, elementId=n['id'], labels=sorted(n['labels']), properties=p))
    keys = {n['elementId']: n['key'] for n in nodes}
    assert len(set(keys.values())) == len(nodes), 'Duplicate stable node keys'
    edges = []
    for r in raw['relationships']:
        assert r['source'] in keys and r['target'] in keys, 'Dangling raw relationship'
        edges.append(dict(key='relationship:' + r['id'], elementId=r['id'],
                          **{'from': keys[r['source']], 'to': keys[r['target']]},
                          type=r['type'], properties=r['properties']))
    assert len({r['key'] for r in edges}) == len(edges), 'Duplicate relationship IDs'
    return dict(nodes=sorted(nodes, key=lambda n: n['key']),
                relationships=sorted(edges, key=lambda r: r['key']))


def subset(graph, node_test, edge_test=lambda r: True):
    nodes = [n for n in graph['nodes'] if node_test(n)]
    keys = {n['key'] for n in nodes}
    edges = [r for r in graph['relationships'] if r['from'] in keys and r['to'] in keys and edge_test(r)]
    return dict(nodes=nodes, relationships=edges)


def visible_concept(n):
    return n['key'].startswith(PREFIX) and n['key'] not in EXCLUDED and bool(
        set(n['labels']) & {'MappingDraftProduct', 'MappingDraftMetric',
                           'MappingDraftEntity', 'MappingDraftOrganization'})


def visible_base(n):
    return visible_concept(n) or (n['key'].startswith(PREFIX) and
        'MappingDraftTable' in n['labels'] and n['properties'].get('tableRole') == 'source')


def business_paths(graph):
    nodes = {n['key']: n for n in graph['nodes']}
    result = []
    for domain, root in [('aum', 'pbconcept:aum_total'), ('income', 'pbconcept:income_total')]:
        types = {'PB_' + domain.upper() + '_MEASURED_BY', 'PB_' + domain.upper() + '_ROLLS_UP_TO'}
        outgoing = {}
        for r in graph['relationships']:
            if r['type'] in types:
                outgoing.setdefault(r['from'], []).append(r)

        def walk(key, path, rels):
            if key == root:
                result.append(dict(domain=domain, nodeKeys=path, relationshipKeys=rels))
                return
            for r in outgoing.get(key, []):
                assert r['to'] not in path, 'Cycle in business measurement paths'
                walk(r['to'], path + [r['to']], rels + [r['key']])

        for key, node in nodes.items():
            if 'PBConceptProduct' in node['labels']:
                walk(key, [key], [])
    return result


def package(source, output):
    downloaded = read(source)
    if isinstance(downloaded, list) and downloaded and 'chunk' in downloaded[0]:
        chunks = sorted(downloaded, key=lambda r: r['chunkIndex'])
        assert [r['chunkIndex'] for r in chunks] == list(range(chunks[0]['chunkCount']))
        assert all(r['chunkCount'] == len(chunks) for r in chunks)
        assert all((r['nodeCount'], r['relationshipCount']) ==
                   (chunks[0]['nodeCount'], chunks[0]['relationshipCount']) for r in chunks)
        text = ''.join(r['chunk'] for r in chunks)
        assert all(r['jsonCharacters'] == len(text) for r in chunks), 'Truncated JSON chunks'
        row = dict(graph=json.loads(text), nodeCount=chunks[0]['nodeCount'],
                   relationshipCount=chunks[0]['relationshipCount'])
    else:
        row = downloaded[0] if isinstance(downloaded, list) else downloaded
    raw = row['graph']
    assert len(raw['nodes']) == row['nodeCount']
    assert len(raw['relationships']) == row['relationshipCount']
    graph = normalize(raw)
    formal = subset(graph, lambda n: 'PBConcept' in n['labels'])
    mapping = subset(graph, lambda n: 'PBConcept' not in n['labels'])
    cross = [r for r in graph['relationships'] if
             r['from'].startswith('pbconcept:') != r['to'].startswith('pbconcept:')]
    base = subset(graph, visible_base, lambda r:
                  r['properties'].get('projectionModel') == 'base_tables_v1' or
                  r['type'] in (CONCEPT_TYPES - {'ASSIGNED_TO'}) | {'IDENTIFIED_IN'})
    projection = subset(graph, visible_concept, lambda r: r['type'] in CONCEPT_TYPES)
    assert not cross, 'Cross-layer links found; retain full download and review scope before splitting'
    assert len(formal['nodes']) + len(mapping['nodes']) == len(graph['nodes'])
    assert len(formal['relationships']) + len(mapping['relationships']) == len(graph['relationships'])
    timestamp = datetime.now(ZoneInfo('Asia/Taipei')).isoformat()
    downloaded_at = datetime.fromtimestamp(source.stat().st_mtime, ZoneInfo('Asia/Taipei')).isoformat()
    date = timestamp[:10].replace('-', '')
    output.mkdir(parents=True, exist_ok=True)
    exports = [
        ('正式概念圖', formal, 'PBConcept：完整業務概念與關係。'),
        ('底表映射圖', base, '現行底表映射檢視：概念、來源底表與關係規則。'),
        ('映射概念檢視', projection, 'MappingDraft 的概念投影；與正式 PBConcept 分開。'),
        ('完整映射與SQL血緣', mapping, '所有非 PBConcept 節點與關係，保留舊映射、SQL 血緣及技術證據。'),
    ]
    files = []
    for name, content, scope in exports:
        manifest = dict(format='offline_property_graph_v1', packagedAt=timestamp,
                        downloadedAt=downloaded_at,
                        source='Neo4j Aura Query → Download JSON', freshlyDownloaded=True,
                        instanceId='4bb479b2', database='neo4j', scope=scope,
                        nodeCount=len(content['nodes']), relationshipCount=len(content['relationships']),
                        labelCounts=dict(Counter(l for n in content['nodes'] for l in n['labels'])),
                        relationshipTypes=dict(Counter(r['type'] for r in content['relationships'])),
                        contentSha256=digest(content), jsonStringPropertiesPreserved=True,
                        credentialsIncluded=False)
        target = output / f'{name}_{date}.json'
        value = dict(manifest=manifest, **content)
        if name == '正式概念圖':
            value['businessPaths'] = business_paths(content)
        dump(target, value)
        roundtrip = read(target)
        assert digest({k: roundtrip[k] for k in ('nodes', 'relationships')}) == manifest['contentSha256']
        files.append(dict(file=target.name, nodeCount=manifest['nodeCount'],
                          relationshipCount=manifest['relationshipCount'],
                          sha256=hashlib.sha256(target.read_bytes()).hexdigest(), bytes=target.stat().st_size))
    shutil.copyfile(source, output / 'Aura_完整原始下載.json')
    dump(output / 'Aura_完整圖譜快照.json', raw)
    extras = output / '本機對照字典'
    extras.mkdir(exist_ok=True)
    for name in ('business_dictionary.json', 'relationship_dictionary.json', 'mapping_routes.json'):
        shutil.copyfile(ROOT / 'ontology/independent_concepts' / name, extras / name)

    # Compare downloaded live properties to local plans without treating plans as the export source.
    canonical = read(ROOT / 'deliverables/graph_exports/20261013/底表映射圖_20261013.json')
    live_nodes = {n['key']: [n['labels'], n['properties']] for n in base['nodes']}
    old_nodes = {n['key']: [sorted(n['labels']), n['properties']] for n in canonical['nodes']}
    live_edges = {r['properties'].get('draftEdgeKey', r['key']):
                  [r['from'], r['type'], r['to'], r['properties']] for r in base['relationships']}
    old_edges = {r['key']: [r['from'], r['type'], r['to'], r['properties']] for r in canonical['relationships']}
    verification = dict(status='passed', packagedAt=timestamp, downloadedAt=downloaded_at,
        freshlyDownloaded=True,
        rawNodes=len(graph['nodes']), rawRelationships=len(graph['relationships']),
        crossLayerRelationships=len(cross), danglingRelationships=0, duplicateNodeKeys=0,
        duplicateRelationshipKeys=0, allPropertiesPreserved=True,
        formalBusinessPathCount=len(business_paths(formal)),
        baseNodesMatch20261013Export=live_nodes == old_nodes,
        baseRelationshipsMatch20261013Export=live_edges == old_edges,
        files=files, externalGraphModified=False,
        dictionariesSource='本機正式字典的輔助對照副本，非本次資料庫匯出')
    dump(output / '匯出核對.json', verification)
    inventory = []
    for path in sorted(output.rglob('*')):
        if path.is_file() and path.suffix != '.zip' and path.name != '檔案清單.json':
            inventory.append(dict(file=path.relative_to(output).as_posix(), bytes=path.stat().st_size,
                                  sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    dump(output / '檔案清單.json', inventory)
    archive_path = output.parent / f'Neo4j_概念與映射圖_{date}.zip'
    with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(output).as_posix())
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
    print(json.dumps(dict(verification=verification, archive=str(archive_path)), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    package(args.source, args.output)
