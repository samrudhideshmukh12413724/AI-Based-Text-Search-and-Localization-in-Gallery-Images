import requests
r = requests.post('http://127.0.0.1:8000/search', json={'query': 'scholarship'})
data = r.json()
results = data.get('results', [])
print(f"Results count: {len(results)}")
for res in results[:3]:
    print(res.get('filename'), res.get('score'), res.get('text_snippet', '')[:50])
