import collections
import json
import pathlib

root = pathlib.Path(r'C:\Users\ngocngothi\Desktop\Rag_thuchanh\RAG')
chunks_dir = root / 'rag_foundation' / 'buoi_05' / 'output' / 'chunks'
files = sorted(chunks_dir.glob('*.json')) if chunks_dir.exists() else []

print('ROOT_OK=' + str((root / 'rag_foundation').exists()))
print('BUOI05_OK=' + str((root / 'rag_foundation' / 'buoi_05').exists()))
print('BUOI06_OK=' + str((root / 'rag_foundation' / 'buoi_06').exists()))
print('CHUNKS_DIR_OK=' + str(chunks_dir.exists()))
print('JSON_COUNT=' + str(len(files)))

for path in files:
    stat = path.stat()
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        valid = True
        kind = 'list' if isinstance(data, list) else 'object' if isinstance(data, dict) else type(data).__name__
        top_keys = list(data.keys())[:10] if isinstance(data, dict) else []
        error = ''
    except Exception as e:
        valid = False
        kind = 'INVALID'
        top_keys = []
        error = str(e)
        data = None

    print('FILE|' + path.name + '|' + str(stat.st_size) + '|' + ('VALID' if valid else 'INVALID') + '|' + kind + '|' + '|'.join(top_keys))
    if valid:
        if isinstance(data, list):
            items = [item for item in data if isinstance(item, dict)]
            presence = {
                'chunk_id': any('chunk_id' in item for item in items),
                'strategy': any('strategy' in item for item in items),
                'source': any('source' in item for item in items),
                'page_start': any('page_start' in item for item in items),
                'page_end': any('page_end' in item for item in items),
                'text': any('text' in item for item in items),
            }
            print('FIELD_PRESENCE|' + path.name + '|' + '|'.join(f'{k}={v}' for k, v in presence.items()))
            strategies = collections.Counter(item.get('strategy') for item in items if isinstance(item, dict) and item.get('strategy'))
            if strategies:
                print('STRATEGIES|' + path.name + '|' + ','.join(f'{k}:{v}' for k, v in strategies.items()))
        elif isinstance(data, dict):
            print('FIELD_PRESENCE|' + path.name + '|chunk_id=' + str('chunk_id' in data) + '|strategy=' + str('strategy' in data) + '|source=' + str('source' in data) + '|page_start=' + str('page_start' in data) + '|page_end=' + str('page_end' in data) + '|text=' + str('text' in data))
    else:
        print('ERROR|' + path.name + '|' + error)

for rel in ['rag.py', 'app.py', '.env.example', 'requirements.txt']:
    path = root / 'rag_foundation' / 'buoi_06' / rel
    print('BUOI06_FILE|' + rel + '|' + ('YES' if path.exists() else 'NO'))
