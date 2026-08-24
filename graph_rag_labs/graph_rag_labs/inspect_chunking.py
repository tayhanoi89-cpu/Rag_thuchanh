import csv
import chunking_pipeline

with open('kb+hops/content.csv', encoding='utf-8-sig', newline='') as handle:
    rows = list(csv.DictReader(handle))

text = chunking_pipeline._clean_html(rows[0]['content_html'])
with open('cleaned_preview.txt', 'w', encoding='utf-8') as handle:
    for line in text.splitlines()[:70]:
        handle.write(line + '\n')
print('wrote cleaned_preview.txt')
