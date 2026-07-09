import urllib.request, json, time

api_key = "0e412ee30d6aa5b309d49f8ab6ba17fa"
series = "DFII10"
url = (
    f"https://api.stlouisfed.org/fred/series/observations"
    f"?series_id={series}&file_type=json&api_key={api_key}"
    f"&observation_start=2024-01-01&observation_end=2024-06-30"
)
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0)"})
t0 = time.time()
resp = urllib.request.urlopen(req, timeout=20)
data = json.loads(resp.read())
elapsed = time.time() - t0
print(f"Status: {resp.status}, Time: {elapsed:.1f}s")
print(f"Keys: {list(data.keys())}")
obs = data.get("observations", [])
print(f"Observations: {len(obs)}")
if obs:
    print(f"First: {obs[0]}")
    print(f"Last: {obs[-1]}")
err = data.get("error_message")
if err:
    print(f"API ERROR: {err}")
