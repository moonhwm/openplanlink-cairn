import zipfile, re, sys
z = zipfile.ZipFile('/tmp/license.docx')
xml = z.read('word/document.xml').decode('utf-8')
text = re.sub(r'<[^>]+>', '', xml)
text = re.sub(r'\s+', ' ', text).strip()
sys.stdout.write(text[:8000])
sys.stdout.write('\n---END---\n')