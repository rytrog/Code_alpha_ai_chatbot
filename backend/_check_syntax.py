import ast
files = [
    'api/chat.py',
    'services/cache_service.py',
    'services/rag_service.py',
    'services/web_search_service.py',
    'utils/text_chunker.py',
    'api/upload.py',
    'config.py',
    'app.py',
]
for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as fh:
            ast.parse(fh.read())
        print(f"{f}: OK")
    except SyntaxError as e:
        print(f"{f}: SYNTAX ERROR at line {e.lineno}: {e.msg}")
print("All syntax checks done.")
