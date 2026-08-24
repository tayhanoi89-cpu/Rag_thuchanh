from pathlib import Path
from chunking_pipeline import build_chunks_from_csv


def walk(node):
    if node.get('type') == 'clause':
        print(node['id'], node['parent_id'], node['title'])
    for child in node.get('children', []):
        walk(child)


documents = build_chunks_from_csv(Path('kb+hops'))
for document in documents:
    walk(document)
