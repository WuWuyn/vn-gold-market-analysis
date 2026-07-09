import urllib.request, json

# Test FRED CSV endpoint
url_csv = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10&cosd=2020-01-01&coed=2020-06-30"
req = urllib.request.Request(url_csv, headers={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/149.0 Safari/537.36"
})
try:
    resp = urllib.request.urlopen(req, timeout=20)
    print(f"CSV OK: {resp.status}, {len(resp.read())} bytes")
except Exception as e:
    print(f"CSV FAIL: {type(e).__name__}: {e}")

# Test FRED API with demo key (should return error or limited data)
url_api = (
    "https://api.stlouisfed.org/fred/series/observations"
    "?series_id=DFII10&file_type=json&api_key=demokey"
    "&observation_start=2020-01-01&observation_end=2020-06-30"
)
req2 = urllib.request.Request(url_api, headers={"User-Agent": "Mozilla/5.0 test"})
try:
    resp2 = urllib.request.urlopen(req2, timeout=20)
    print(f"API OK: {resp2.status}")
    txt = resp2.read().decode()
    # May be empty or error
    print(f"API body first 200 chars: {txt[:200]}")
except Exception as e:
    print(f"API FAIL: {type(e).__name__}: {e}")
