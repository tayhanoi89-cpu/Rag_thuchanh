from pathlib import Path
from chunking_pipeline import build_chunks_from_csv


def walk(node, path='root'):
    if 'id' not in node:
        print('MISSING ID', path, node.get('type'), repr(node.get('title')))
        return True
    for child in node.get('children', []):
        if walk(child, f"{path}/{node.get('type')}"):
            return True
    return False


documents = build_chunks_from_csv(Path('kb+hops'))
for doc in documents:
    print('document', doc['id'], doc['title'])
    for child in doc.get('children', []):
        if walk(child, doc['id']):
            break
    else:
        continue
    break
