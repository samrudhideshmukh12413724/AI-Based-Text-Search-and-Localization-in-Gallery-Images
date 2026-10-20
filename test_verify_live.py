import urllib.request, json, time

for i in range(15):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2) as r:
            if r.status == 200:
                print('Server is healthy and ready!')
                break
    except Exception:
        time.sleep(1)

def do_search(q):
    req = urllib.request.Request(
        'http://127.0.0.1:8000/search',
        data=json.dumps({'query': q}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        d = json.loads(resp.read().decode())
        print(f"\n=== Query: '{q}' ===")
        print(f"Total Count: {d.get('count')}")
        for res in d.get('results', [])[:5]:
            print(f"  ID: {res.get('id')} | Image: {res.get('image_name')} | Score: {res.get('similarity_score')} | Type: {res.get('search_type')}")

do_search('1890')
do_search('desai')
do_search('qr')
do_search('dvc')
do_search('ollama')
do_search('sha')
do_search('fees')
do_search('scholarship')
