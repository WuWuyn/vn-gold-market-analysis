import urllib.request, json, time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0 Safari/537.36",
    "Accept": "text/csv,*/*",
    "Accept-Language": "en,vi;q=0.9",
    "Connection": "close",
}

# Test 1: FRED CSV (blocked?)
url1 = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10&cosd=2024-01-01&coed=2024-01-15"
try:
    req = urllib.request.Request(url1, headers=headers)
    t0 = time.time()
    resp = urllib.request.urlopen(req, timeout=20)
    data = resp.read()
    print(f"FRED CSV: OK ({len(data)} bytes, {time.time()-t0:.1f}s)")
    print(data[:200].decode())
except Exception as e:
    print(f"FRED CSV: FAIL {type(e).__name__}: {e}")

# Test 2: yfinance GLD via Ticker API
try:
    import yfinance as yf
    t = yf.Ticker("GLD")
    h = t.history(start="2025-01-01", auto_adjust=False, progress=False)
    print(f"GLD Ticker: {len(h)} rows")
except Exception as e:
    print(f"GLD Ticker: FAIL {type(e).__name__}: {e}")

# Test 3: yfinance GC=F via Ticker API
try:
    t2 = yf.Ticker("GC=F")
    h2 = t2.history(start="2025-01-01", auto_adjust=False, progress=False)
    print(f"GC=F Ticker: {len(h2)} rows")
except Exception as e:
    print(f"GC=F Ticker: FAIL {type(e).__name__}: {e}")
