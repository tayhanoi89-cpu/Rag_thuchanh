from pathlib import Path
import sys
import tempfile

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root))
from rag_advance.buoi_09.hierarchical_rag import build_store

fixture = root / 'rag_advance' / 'buoi_09' / 'tests' / 'fixtures' / 'hierarchical_sample.json'
with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp)
    result = build_store(input_path=fixture, output_dir=out, config={'PARENT_MAX_CHARS': 4000})
    print('children', [c['child_id'] for c in result['children']])
    print('parents', [p['parent_id'] for p in result['parents']])
    print('mapping:')
    for p in result['parents']:
        print('parent', p['parent_id'], 'children', p['child_ids'])
