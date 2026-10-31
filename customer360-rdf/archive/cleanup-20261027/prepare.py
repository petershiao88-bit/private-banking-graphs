"""One-time, read/hash/copy-only preparation of the 2026-10-27 cleanup."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
old = ['HANDOFF-ZED-RDF-20261021.md', 'MIGRATION-v0.3.0.md', 'README.txt',
       'tools/legacy-v0.2.0', 'tools/seed_investment_metrics.py',
       'tools/seed_product_aum.py', 'tools/seed_product_fees.py']
old += ['outputs/' + p.name for p in (ROOT/'outputs').iterdir()
        if p.name not in ('fabric-v0.16.0', 'fabric-v0.16.0.zip')]
old += ['semantica-poc/' + p for p in ('vendor', 'owl_reasoner.py', 'reasoner_worker.py',
        'test_owl_reasoner.py', 'requirements-reasoning.txt', 'logs',
        'data/reasoner-io', 'data/reasoning', 'data/graph-qa.jpg', 'data/llm-hermit.jpg',
        'data/reasoning-browser-example.json', 'data/reasoning-live-checks.json',
        'data/reasoning-verification.json')]
plans = [(p, 'archive/cleanup-20261027/' + p) for p in old if (ROOT/p).exists()]
plans += [(f'department-pg/{p}', f'archive/department-pg/{p}') for p in ('history', 'drafts')]
plans += [(str(p.relative_to(ROOT)).replace('\\','/'), 'tests/pg/' + p.name)
          for p in sorted((ROOT/'department-pg').glob('*.py'))
          if p.name.startswith(('test_', 'review_contract'))]
records = []
for src, dst in plans:
    a, b = ROOT/src, ROOT/dst
    assert a.exists() and not b.exists(), (src, dst)
    assert a.resolve().is_relative_to(ROOT) and b.resolve().is_relative_to(ROOT)
    files = [a] if a.is_file() else sorted(p for p in a.rglob('*') if p.is_file())
    records.append({'source':src, 'destination':dst, 'files':[
        {'path': str(f.relative_to(a)).replace('\\','/') if a.is_dir() else '',
         'sha256':sha(f), 'bytes':f.stat().st_size} for f in files]})
backups = ['README.md', 'department-pg/README.md', 'department-pg/METRIC-TABLE-SOURCES.md',
           'tools/export_metric_tables.py', 'semantica-poc/README.md',
           'semantica-poc/UI-VERIFICATION.md', 'pyrightconfig.json']
backups += [s for s,d in plans if d.startswith('tests/pg/')]
for rel in backups:
    target = DEST/'before-edits'/rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT/rel, target)
shutil.copy2(ROOT.parent/'README.md', DEST/'before-edits/customer360-parent-README.md')
(DEST/'move-manifest.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'moves':len(records), 'files':sum(len(r['files']) for r in records)}, ensure_ascii=False))
