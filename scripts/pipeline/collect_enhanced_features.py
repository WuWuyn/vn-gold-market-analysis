#!/usr/bin/env python3
"""
Enhanced external features collector (v2).

Uses FRED JSON API for: DFII10, T10YIE, T5YIE, STLFSI2, NFCI, BAA10Y, AAA10Y, M2SL,
DGS10, VIXCLS, DTWEXBGS, DCOILWTICO, GLD.

Uses yfinance Ticker API for: GLD ETF, GC=F futures, GLD shares outstanding.

Uses crawl4ai for: LBMA Gold Fix (London spot reference).

VN deposit rates via SBV headless JSON CMS API.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import sys
import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib import request as _url_request, error as _url_error, parse as _url_parse

try:
    from ._bootstrap import bootstrap
except ImportError:
    from _bootstrap import bootstrap

bootstrap()

from gold_collectors.full_pipeline import DataLakeWriter

# ---------------------------------------------------------------------------
# FRED series mapping (series_id -> (asset_name, unit))
# ---------------------------------------------------------------------------
ENHANCED_FRED_SERIES: dict[str, tuple[str, str]] = {
    "DGS10": ("us_10y_nominal", "pct"),
    "DCOILWTICO": ("wti_crude", "usd_barrel"),
    "VIXCLS": ("vix", "index"),
    "DTWEXBGS": ("dxy_broad", "index"),
    "DFII10": ("us_10y_real_tips_yield", "pct"),
    "T10YIE": ("us_10y_breakeven_inflation", "pct"),
    "T5YIE": ("us_5y_breakeven_inflation", "pct"),
    "STLFSI2": ("st_louis_financial_stress", "index"),
    "NFCI": ("chicago_fed_national_fin_conditions", "index"),
    "BAA10Y": ("baa_corp_bond_yield", "pct"),
    "AAA10Y": ("aaa_corp_bond_yield", "pct"),
    "M2SL": ("m2_money_supply", "billions_usd"),
    "GLD": ("gld_spdr_gold_etf_close", "usd"),
}

FRED_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# FRED collector via JSON API
# ---------------------------------------------------------------------------
def collect_enhanced_fred(start: str, end: str) -> list[dict[str, Any]]:
    """Fetch all FRED series via official JSON API."""
    api_key = os.environ.get("FRED_API_KEY", "")
    if not api_key:
        print(" FRED: No FRED_API_KEY found, skipping")
        return []

    rows: list[dict[str, Any]] = []

    for series_id, (asset, unit) in ENHANCED_FRED_SERIES.items():
        url = (
            "https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&file_type=json&api_key={api_key}"
            f"&observation_start={start}&observation_end={end}"
            "&limit=50000&sort_order=asc"
        )
        try:
            req = _url_request.Request(
                url,
                headers={"User-Agent": FRED_USER_AGENT, "Accept": "application/json"},
            )
            with _url_request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                payload = json.loads(raw.decode("utf-8", errors="replace"))
                raw_hash = hashlib.sha256(raw).hexdigest()
        except _url_error.HTTPError as exc:
            print(f" FRED {series_id}: HTTP {exc.code} - {exc.reason}")
            continue
        except Exception as exc:
            print(f" FRED {series_id}: {type(exc).__name__}: {exc}")
            continue

        if "error_message" in payload:
            print(f" FRED {series_id}: API error - {payload['error_message']}")
            continue

        obs_count = 0
        for item in payload.get("observations", []):
            val = item.get("value", "")
            if val in ("", ".", None):
                continue
            try:
                value = float(val)
            except ValueError:
                continue
            obs_date = item.get("date", "")
            if not obs_date:
                continue
            rows.append(
                {
                    "date": obs_date[:10],
                    "series_id": series_id,
                    "asset": asset,
                    "value": value,
                    "unit": unit,
                    "source": "fred_json_v2",
                    "raw_hash": raw_hash,
                    # FIX: available_from = realtime_start from FRED
                    "available_from": item.get("realtime_start", obs_date[:10]),
                }
            )
            obs_count += 1
        print(f" FRED {series_id}: {obs_count} observations")

    return rows


# ---------------------------------------------------------------------------
# yfinance Ticker-based collector
# ---------------------------------------------------------------------------
def _collect_yfinance_ticker(
    symbol: str, asset_name: str, start: str, end: str
) -> list[dict[str, Any]]:
    """Download OHLCV via yfinance Ticker API."""
    import yfinance as yf  # noqa: delayed import

    rows: list[dict[str, Any]] = []
    ticker = yf.Ticker(symbol)
    end_excl = (
        datetime.strptime(end, "%Y-%m-%d").date() + timedelta(days=1)
    ).isoformat()
    frame = ticker.history(
        start=start, end=end_excl, auto_adjust=False, repair=False
    )
    if frame.empty:
        return rows

    for idx, row in frame.iterrows():
        d = idx.date().isoformat()
        close_v = row.get("Close")
        if close_v is None:
            continue
        rows.append(
            {
                "date": d,
                "series_id": symbol,
                "asset": asset_name,
                "value": round(float(close_v), 4),
                "open": round(float(row["Open"]), 4)
                if row.get("Open") is not None
                else None,
                "high": round(float(row["High"]), 4)
                if row.get("High") is not None
                else None,
                "low": round(float(row["Low"]), 4)
                if row.get("Low") is not None
                else None,
                "volume": round(float(row["Volume"]), 0)
                if row.get("Volume") is not None
                else None,
                "unit": "usd_per_share",
                "source": "yfinance_ticker_v2",
                "note": "no_shares_outstanding",
                # FIX: available_from = date+1 (US market close lag for VN)
                "available_from": (
                    datetime.strptime(d, "%Y-%m-%d").date() + timedelta(days=1)
                ).isoformat(),
            }
        )
    return rows


def collect_gld_etf(start: str, end: str) -> list[dict[str, Any]]:
    return _collect_yfinance_ticker("GLD", "gld_spdr_gold_etf", start, end)


def collect_gc_futures(start: str, end: str) -> list[dict[str, Any]]:
    return _collect_yfinance_ticker("GC=F", "gold_futures_front_continuous", start, end)


# ---------------------------------------------------------------------------
# Gold futures basis
# ---------------------------------------------------------------------------
def collect_gold_futures_basis(start: str, end: str) -> list[dict[str, Any]]:
    """Collect GC=F as primary futures proxy."""
    return collect_gc_futures(start, end)


# ---------------------------------------------------------------------------
# LBMA Gold Fix via crawl4ai
# ---------------------------------------------------------------------------
def collect_lbma_gold_price() -> list[dict[str, Any]]:
    """Scrape LBMA Gold Fix prices from lbma.org.uk price history page."""
    rows: list[dict[str, Any]] = []
    try:
        from crawl4ai import AsyncWebCrawler, CacheMode  # noqa: optional
    except ImportError:
        print(" LBMA: crawl4ai not installed, skipping")
        return rows

    async def _crawl() -> None:
        async with AsyncWebCrawler(
            headless=True, cache_mode=CacheMode.BYPASS
        ) as crawler:
            targets = [
                "https://www.lbma.org.uk/lbma-gold-price-data",
                "https://www.lbma.org.uk/lbma-gold-price",
            ]
            for url in targets:
                try:
                    r = await crawler.arun(
                        url=url,
                        word_count_threshold=1,
                        page_timeout=20_000,
                        js_code="() => { const rows = document.querySelectorAll('table tbody tr'); return Array.from(rows).slice(0,200).map(r => r.innerText).join('\\n'); }",
                    )
                    text = r.markdown or ""
                    raw_hash = hashlib.sha256(text.encode()).hexdigest()
                    count = 0
                    for line in text.split("\n"):
                        m = re.search(
                            r"(\d{1,2}/\d{1,2}/\d{4})\s+(\d{2,4}[.,]\d{2})", line
                        )
                        if m:
                            date_str, val = m.group(1), m.group(2)
                            try:
                                d = datetime.strptime(date_str, "%d/%m/%Y").date().isoformat()
                            except ValueError:
                                continue
                            try:
                                v = float(val.replace(",", "."))
                            except ValueError:
                                continue
                            rows.append(
                                {
                                    "date": d,
                                    "series_id": "LBMA_GOLD_FIX",
                                    "asset": "lbma_gold_fix_usd_oz",
                                    "value": v,
                                    "unit": "usd_per_oz",
                                    "source": "lbma_crawl4ai",
                                    "raw_hash": raw_hash,
                                    "available_from": d,
                                }
                            )
                            count += 1
                    print(
                        f" LBMA [{url.split('/')[-1]}]: {count} prices from {len(text)} chars"
                    )
                except Exception as exc:
                    print(f" LBMA error [{url}]: {type(exc).__name__}: {exc}")

    # FIX: handle RuntimeError when already in an event loop
    try:
        import asyncio
        asyncio.run(_crawl())
    except RuntimeError:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(lambda: asyncio.run(_crawl())).result(timeout=120)

    return rows


# ---------------------------------------------------------------------------
# GLD shares outstanding
# ---------------------------------------------------------------------------
def collect_gld_shares_outstanding() -> list[dict[str, Any]]:
    """One-row snapshot: GLD total shares outstanding right now."""
    rows: list[dict[str, Any]] = []
    try:
        import yfinance as yf  # noqa: delayed import
        t = yf.Ticker("GLD")
        so_val = t.info.get("sharesOutstanding")
        if so_val and so_val > 0:
            today = date.today().isoformat()
            rows.append(
                {
                    "date": today,
                    "series_id": "GLD_SHARES_OUTSTANDING",
                    "asset": "gld_etf_shares_outstanding",
                    "value": float(so_val),
                    "unit": "shares",
                    "source": "yfinance_gld_info",
                    "available_from": today,
                    "note": f"SPDR Gold Shares - {so_val/1e6:.1f}M shares; current snapshot",
                }
            )
            print(f" GLD shares outstanding: {so_val/1e6:.1f}M")
        else:
            print(" GLD shares outstanding: yfinance returned null/zero")
    except Exception as exc:
        print(f" GLD shares outstanding error: {type(exc).__name__}: {exc}")
    return rows


# ---------------------------------------------------------------------------
# VN deposit rates (SBV headless JSON API)
# ---------------------------------------------------------------------------
_VN_DEPOSIT_CONTENT_STRUCTURE_ID = "137473"


def collect_vietnam_deposit_rates() -> list[dict[str, Any]]:
    """Fetch SBV deposit rate announcements via headless delivery JSON API."""
    rows: list[dict[str, Any]] = []
    url = (
        f"https://www.sbv.gov.vn/vi/o/headless-delivery/v1.0/content-structures/"
        f"{_VN_DEPOSIT_CONTENT_STRUCTURE_ID}/structured-contents"
        f"?pageSize=50&sort=datePublished:desc"
    )
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    }
    try:
        req = _url_request.Request(url, headers=headers)
        with _url_request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            payload = json.loads(raw.decode("utf-8", errors="replace"))
            raw_hash = hashlib.sha256(raw).hexdigest()
    except Exception as exc:
        print(f" SBV deposit rates API: {type(exc).__name__}: {exc}")
        return rows

    items = payload.get("items", [])
    if not items:
        print(" SBV deposit rates API: empty response")
        return rows

    print(f" SBV deposit rates API: {len(items)} items")

    # --- FIX: First, inspect actual field names to build mapping ---
    # Print field names from first 3 items for debugging
    field_names_seen: set[str] = set()
    for item in items[:3]:
        for field in item.get("contentFields", []):
            fn = field.get("name", "")
            if fn:
                field_names_seen.add(fn)
    print(f" SBV field names in first 3 items: {sorted(field_names_seen)}")

    for item in items:
        fields: dict[str, str] = {}
        for field in item.get("contentFields", []):
            value = field.get("contentFieldValue") or {}
            fields[field.get("name", "")] = str(value.get("data", "") or "")

        pub_date = item.get("datePublished", "")[:10]
        if not pub_date:
            continue

        # Try multiple field name patterns (case-insensitive, underscore/space agnostic)
        rate_value = _parse_sbv_rate_text(fields)
        doc_number = (
            fields.get("SoVanBan")
            or fields.get("SoVanBanThongBao")
            or fields.get("So_van_ban")
            or fields.get("so_van_ban")
            or ""
        )

        rows.append(
            {
                "date": pub_date,
                "source": "sbv_deposit_rates_json",
                "series_id": "SBV_DEPOSIT_RATES",
                "asset": "vn_deposit_rates",
                "value": rate_value,
                "unit": "pct",
                "document_number": doc_number,
                "published_at": item.get("datePublished"),
                "available_from": pub_date,
                "raw_hash": raw_hash,
                "note": f"fields={','.join(sorted(fields.keys())[:5])}",
            }
        )

    # Deduplicate by date+doc_number
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for r in rows:
        key = (r["date"], r.get("document_number", ""))
        if key not in seen:
            seen.add(key)
            unique.append(r)

    print(f" SBV deposit rates: {len(unique)} unique entries")
    non_null = sum(1 for r in unique if r.get("value") is not None)
    print(f" SBV non-null values: {non_null}/{len(unique)}")
    return unique


def _parse_sbv_rate_text(fields: dict[str, str]) -> float | None:
    """Extract a representative rate from SBV content fields."""
    # FIX: Broader keyword matching + strip accents
    import unicodedata

    def _strip(s: str) -> str:
        return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

    candidates: list[float] = []
    for name, value in fields.items():
        if not value:
            continue
        name_stripped = _strip(name).lower()
        if any(kw in name_stripped for kw in [
            "laisuat", "lai_suat", "laisu", "rate", "ty_le", "tyle",
            "lai", "philyphi", "deposit", "gui", "tien"
        ]):
            try:
                v = float(str(value).replace(",", ".").replace("%", "").strip())
                if 0 < v < 100:  # sanity check
                    candidates.append(v)
            except (ValueError, TypeError):
                pass

    if candidates:
        candidates.sort()
        mid = len(candidates) // 2
        return candidates[mid] if len(candidates) % 2 == 1 else (candidates[mid - 1] + candidates[mid]) / 2

    # Broader fallback: scan ALL values for % patterns
    for value in fields.values():
        text = str(value)
        m = re.search(r"(\d{1,2}[.,]\d{1,2})\s*%", text)
        if m:
            try:
                v = float(m.group(1).replace(",", "."))
                if 0 < v < 100:
                    return v
            except ValueError:
                pass

    return None


# ---------------------------------------------------------------------------
# VN macro extractor (Task #2) — direct call into extract_vn_macro
# ---------------------------------------------------------------------------
def collect_vn_macro(from_date: str, to_date: str) -> list[dict[str, Any]]:
    """Call extract_vn_macro to get high-signal GSO indicators."""
    # We reuse the logic inline to avoid subprocess
    input_csv = "data/lake/external_features/normalized/macro_series.csv"
    try:
        rows, _ = _extract_vn_macro_inline(input_csv, from_date, to_date)
        return rows
    except Exception as exc:
        print(f" VN macro extract: {type(exc).__name__}: {exc}")
        return []


# Inline copy of the indicator map so we don't import the script
_HIGH_SIGNAL: dict[str, tuple[str, str, str]] = {
    "PCPI_IX": ("cpi_headline_yoy_pct", "pct", "M"),
    "AIP_ISIC4_IX": ("ip_total_index", "index_2015=100", "M"),
    "AIP_ISIC4_B_IX": ("ip_mining_quarrying_index", "index_2015=100", "M"),
    "AIP_ISIC4_C_IX": ("ip_manufacturing_index", "index_2015=100", "M"),
    "AIP_ISIC4_D_IX": ("ip_electricity_index", "index_2015=100", "M"),
    "AIP_ISIC4_E_IX": ("ip_water_waste_index", "index_2015=100", "M"),
    "LE_PE_NUM": ("labour_employed_10k", "10k_persons", "Q"),
    "LLF_PE_NUM": ("labour_force_10k", "10k_persons", "Q"),
    "LEU_PT": ("unemployment_rate_pct", "pct", "Q"),
    "TMG_CIF_USD": ("total_imports_cif_m_usd", "M_USD", "M"),
    "TMGIOT_CIF_USD": ("imports_all_cif_m_usd", "M_USD", "M"),
    "TMGISO_CIF_USD": ("imports_direct_m_usd", "M_USD", "M"),
    "VNM_HNX_EOP_IX": ("hnx_index_eop", "index", "M"),
    "VNM_VN_EOP_IX": ("vnindex_eop", "index", "M"),
    "LP_PE_NUM": ("population_10k", "10k_persons", "A"),
}
_SERIES_LOOKUP: dict[str, tuple[str, str, str]] = dict(_HIGH_SIGNAL)


def _extract_vn_macro_inline(
    input_csv: str, from_date: str, to_date: str
) -> tuple[list[dict[str, Any]], dict]:
    from_dt = date.fromisoformat(from_date)
    to_dt = date.fromisoformat(to_date)
    merged: dict[str, list[dict]] = {sid: [] for sid in _HIGH_SIGNAL}
    with open(input_csv, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sid = row.get("series_id", "")
            if sid not in _SERIES_LOOKUP:
                continue
            d_str = row.get("date", "")[:10]
            if not d_str:
                continue
            try:
                d = date.fromisoformat(d_str)
            except ValueError:
                continue
            if d < from_dt or d > to_dt:
                continue
            val_raw = row.get("value", "")
            if not val_raw:
                continue
            try:
                val = float(val_raw)
            except (ValueError, TypeError):
                continue
            friendly_name, unit, _ = _SERIES_LOOKUP[sid]
            available_from = row.get("release_date", "") or d.isoformat()
            merged[sid].append(
                {
                    "date": d.isoformat(),
                    "series_id": sid,
                    "series_name": friendly_name,
                    "frequency": row.get("frequency", ""),
                    "value": val,
                    "unit": unit,
                    "source": "gso_macro_monitor_curated",
                    "domain": row.get("domain", ""),
                    "available_from": available_from[:10] if available_from else d.isoformat(),
                    "release_date": row.get("release_date", ""),
                }
            )
    out: list[dict[str, Any]] = []
    for sid, rows_list in merged.items():
        out.extend(rows_list)
    out.sort(key=lambda x: (x["date"], x["series_id"]))
    manifest = {
        "generated_at": date.today().isoformat(),
        "from": from_date,
        "to": to_date,
        "indicators_extracted": len(_HIGH_SIGNAL),
        "indicators_with_data": sum(1 for r in merged.values() if r),
        "indicators_missing": [sid for sid, r in merged.items() if not r],
        "total_rows": len(out),
    }
    return out, manifest


# ---------------------------------------------------------------------------
# Wedding season (Task #4)
# ---------------------------------------------------------------------------
def collect_wedding_season(from_date: str, to_date: str) -> list[dict[str, Any]]:
    """Generate wedding season event records (Apr-May + Aug-Oct)."""
    from datetime import date as _date

    rows: list[dict[str, Any]] = []
    fd = _date.fromisoformat(from_date)
    td = _date.fromisoformat(to_date)

    year = fd.year
    while year <= td.year:
        # Spring: Apr 15-May 31
        for month, day, sev in [(4, 15, "medium"), (5, 1, "high")]:
            d = _date(year, month, day)
            if fd <= d <= td:
                rows.append({
                    "event_date": d.isoformat(),
                    "event_type": "wedding_season",
                    "severity": sev,
                    "scope": "domestic_vietnam",
                    "expected_channel": "premium_spike",
                    "note": "Traditional wedding season — gold jewelry demand surge",
                    "source": "rule_based_calendar",
                    "available_from": d.isoformat(),
                })
        # Autumn: Aug 15-Oct 5
        for month, day, sev in [(8, 15, "high"), (9, 1, "high"), (10, 1, "high")]:
            d = _date(year, month, day)
            if fd <= d <= td:
                rows.append({
                    "event_date": d.isoformat(),
                    "event_type": "wedding_season",
                    "severity": sev,
                    "scope": "domestic_vietnam",
                    "expected_channel": "premium_spike",
                    "note": "Autumn wedding season — gold jewelry demand surge",
                    "source": "rule_based_calendar",
                    "available_from": d.isoformat(),
                })
        year += 1

    print(f" Wedding season: {len(rows)} event rows")
    return rows


# ---------------------------------------------------------------------------
# News/sentiment via RSS (Task #5)
# ---------------------------------------------------------------------------
_FEEDS: list[dict[str, str]] = [
    {"name": "vnexpress_gold", "url": "https://vnexpress.net/rss/gold.rss", "lang": "vi", "category": "gold_vn"},
    {"name": "vnexpress_economy", "url": "https://vnexpress.net/rss/kinh-te.rss", "lang": "vi", "category": "economy"},
    {"name": "vnexpress_world", "url": "https://vnexpress.net/rss/the-gioi.rss", "lang": "vi", "category": "geopolitics"},
    {"name": "tuoitre_news", "url": "https://tuoitrenews.vn/rss/front.rss", "lang": "vi", "category": "news"},
    {"name": "google_news_vn_gold", "url": "https://news.google.com/rss/search?q=vietnam+gold+sjc&hl=vi&gl=VN&ceid=VN:vi", "lang": "vi", "category": "gold_vn"},
]

_GOLD_VI = ["vang", "sjc", "pnj", "gia vang", "nhan vang", "mua vang", "ban vang",
            "kim loai quy", "gold", "ounce", "oz", "ty gia vang", "premium",
            "lai suat", "lai suat gui", "sbv", "nnvn", "ty gia", "usd", "vnd"]
_GOLD_EN = ["gold", "xau", "gld", "gold price", "gold futures", "spot gold",
            "lbma", "comex", "fed", "interest rate", "yield", "treasury",
            "usd", "dxy", "dollar", "inflation", "cpi", "tips"]
_POSITIVE_VI = {"tang", "tang gia", "huong", "mua vao", "lai", "loi nhuan",
                "ky vong", "tich cuc", "phuc hoi"}
_NEGATIVE_VI = {"giam", "giam gia", "ban ra", "lo", "suy thoa", "lo ngai",
                "cang thang", "kho khan", "sup do"}
_POSITIVE_EN = {"rise", "surge", "gain", "rally", "bullish", "recovery", "strong"}
_NEGATIVE_EN = {"fall", "plunge", "crash", "bearish", "recession", "crisis", "collapse"}


def _fetch_rss(url: str, timeout: int = 20) -> str | None:
    try:
        req = _url_request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0",
                "Accept": "application/rss+xml,*/*",
            },
        )
        with _url_request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f" RSS fetch [{url[:50]}]: {type(exc).__name__}")
        return None


def collect_news_rss(from_date: str, to_date: str, timeout: int = 20) -> list[dict[str, Any]]:
    """Collect headlines from RSS feeds with relevance + sentiment scoring."""
    from datetime import date as _date
    import hashlib as _hashlib

    rows: list[dict[str, Any]] = []
    from_dt = _date.fromisoformat(from_date)
    to_dt = _date.fromisoformat(to_date)
    seen_hashes: set[str] = set()

    for feed in _FEEDS:
        xml = _fetch_rss(feed["url"], timeout)
        if not xml:
            continue

        items_added = 0
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml)
            entries = root.findall(".//item") or root.findall(
                ".//{http://www.w3.org/2005/Atom}entry"
            )
        except ET.ParseError as exc:
            print(f" RSS parse [{feed['name']}]: {exc}")
            continue

        lang = feed["lang"]
        kws = _GOLD_VI if lang == "vi" else _GOLD_EN
        pos = _POSITIVE_VI if lang == "vi" else _POSITIVE_EN
        neg = _NEGATIVE_VI if lang == "vi" else _NEGATIVE_EN

        for entry in entries:
            title_el = entry.find("title")
            link_el = entry.find("link")
            date_el = entry.find("pubDate") or entry.find(
                "{http://www.w3.org/2005/Atom}updated"
            ) or entry.find("{http://www.w3.org/2005/Atom}published")
            if title_el is None or not (title_el.text or "").strip():
                continue
            title = (title_el.text or "").strip()
            link = ""
            if link_el is not None:
                link = (link_el.text or "").strip() or link_el.get("href", "")
            pub_raw = (date_el.text or "").strip() if date_el is not None else ""

            # Parse date
            pub_iso = ""
            if pub_raw:
                for fmt in (
                    "%a, %d %b %Y %H:%M:%S %z",
                    "%Y-%m-%dT%H:%M:%S%z",
                    "%Y-%m-%dT%H:%M:%SZ",
                ):
                    try:
                        pub_iso = datetime.strptime(
                            pub_raw[:len(fmt.replace("%Y", "0000").replace("%b", "MMM").replace("%z", "+0000"))],
                            fmt,
                        ).date().isoformat()
                        break
                    except (ValueError, TypeError):
                        continue
                if not pub_iso:
                    pub_iso = pub_raw[:10]

            if not pub_iso:
                continue
            try:
                d = _date.fromisoformat(pub_iso)
            except ValueError:
                continue
            if d < from_dt or d > to_dt:
                continue

            # Dedup
            h = _hashlib.sha256(title.encode()).hexdigest()[:16]
            if h in seen_hashes:
                continue
            seen_hashes.add(h)

            matched = [kw for kw in kws if kw.lower() in title.lower()]
            relevance = len(matched)
            pos_hits = sum(1 for w in pos if w.lower() in title.lower())
            neg_hits = sum(1 for w in neg if w.lower() in title.lower())
            if pos_hits > neg_hits:
                sentiment = "positive"
            elif neg_hits > pos_hits:
                sentiment = "negative"
            elif relevance == 0:
                sentiment = "irrelevant"
            else:
                sentiment = "neutral"

            rows.append(
                {
                    "date": pub_iso,
                    "source": feed["name"],
                    "title": title,
                    "url": link,
                    "lang": lang,
                    "category": feed["category"],
                    "keyword_matches": " ".join(matched),
                    "relevance_score": relevance,
                    "sentiment_heuristic": sentiment,
                    "sentiment_score_raw": round(
                        (pos_hits - neg_hits) / max(pos_hits + neg_hits, 1), 2
                    ),
                    "raw_hash": h,
                    "available_from": pub_iso,
                }
            )
            items_added += 1

        print(f" RSS [{feed['name']}]: {items_added} new items")

    rows.sort(key=lambda x: (x["date"], x["source"]))
    return rows


# ---------------------------------------------------------------------------
# Policy events (Task #11 supplement)
# ---------------------------------------------------------------------------
def collect_policy_events() -> list[dict[str, Any]]:
    """Manually curated policy events affecting VN gold premium."""
    return [
        {
            "event_date": "2024-03-14",
            "event_type": "policy_auction",
            "severity": "high",
            "scope": "domestic_vietnam",
            "expected_channel": "premium_shrink",
            "note": "NHNN restarts gold auction after 11-year hiatus (Decision 319/QD-NHNN)",
            "source": "manual_curation",
            "available_from": "2024-03-14",
        },
        {
            "event_date": "2024-06-14",
            "event_type": "policy_auction",
            "severity": "medium",
            "scope": "domestic_vietnam",
            "expected_channel": "premium_shrink",
            "note": "NHNN 5th gold auction — 300 taels sold at floor price",
            "source": "manual_curation",
            "available_from": "2024-06-14",
        },
        {
            "event_date": "2025-01-03",
            "event_type": "policy_rate_increase",
            "severity": "high",
            "scope": "domestic_vietnam",
            "expected_channel": "premium_shrink",
            "note": "SBV raised refinance rate from 4.5% to 5.0% — first hike in years",
            "source": "manual_curation",
            "available_from": "2025-01-03",
        },
        {
            "event_date": "2015-01-05",
            "event_type": "geopolitical_crisis",
            "severity": "high",
            "scope": "global",
            "expected_channel": "premium_spike",
            "note": "NĐ/dong devaluation ~2% — major VND shock, gold domestic price surged",
            "source": "manual_curation",
            "available_from": "2015-01-05",
        },
        {
            "event_date": "2022-03-08",
            "event_type": "geopolitical_crisis",
            "severity": "high",
            "scope": "global",
            "expected_channel": "premium_spike",
            "note": "Russia-Ukraine war started — safe haven demand, gold global spike",
            "source": "manual_curation",
            "available_from": "2022-03-08",
        },
        {
            "event_date": "2024-07-18",
            "event_type": "policy_import",
            "severity": "medium",
            "scope": "domestic_vietnam",
            "expected_channel": "liquidity_improve",
            "note": "SBV imported additional gold to boost domestic supply",
            "source": "manual_curation",
            "available_from": "2024-07-18",
        },
        {
            "event_date": "2024-11-01",
            "event_type": "policy_import",
            "severity": "medium",
            "scope": "domestic_vietnam",
            "expected_channel": "liquidity_improve",
            "note": "SBV second gold import batch — 20 tonnes announced",
            "source": "manual_curation",
            "available_from": "2024-11-01",
        },
    ]


# ---------------------------------------------------------------------------
# GLD historical shares outstanding (Task #6)
# ---------------------------------------------------------------------------
def collect_gld_shares_historical(from_date: str, to_date: str) -> list[dict[str, Any]]:
    """Fetch GLD shares outstanding history from publicly available sources.

    Primary: SEC EDGAR NPORT-P filings
    Fallback: yfinance .info (current only, stored with action='fill_forward')
    """
    rows: list[dict[str, Any]] = []

    # Approach 1: Try SEC EDGAR for NPORT filings with GLD holdings
    try:
        import json as _json
        sec_url = (
            "https://data.sec.gov/api/xbrl/companyfacts/CIK0001108524.json"
        )
        req = _url_request.Request(
            sec_url,
            headers={
                "User-Agent": "vn-gold-pipeline research@example.com",
                "Accept": "application/json",
            },
        )
        with _url_request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            payload = _json.loads(raw.decode("utf-8", errors="replace"))
            raw_hash = hashlib.sha256(raw).hexdigest()

        # Look for US-GAAP shares outstanding facts
        facts = payload.get("facts", {}).get("us-gaap", {})
        shares_key = "CommonStockSharesOutstanding"
        if shares_key not in facts:
            shares_key = "WeightedAverageNumberOfSharesOutstandingBasic"
        if shares_key in facts:
            units = facts[shares_key].get("units", {}).get("shares", [])
            from_dt = date.fromisoformat(from_date)
            to_dt = date.fromisoformat(to_date)
            for u in units:
                end_d = u.get("end", "")[:10]
                if not end_d:
                    continue
                try:
                    d = date.fromisoformat(end_d)
                except ValueError:
                    continue
                if from_dt <= d <= to_dt:
                    val = u.get("val")
                    if val and val > 0:
                        rows.append(
                            {
                                "date": end_d,
                                "series_id": "GLD_SHARES_OUTSTANDING",
                                "asset": "gld_etf_shares_outstanding",
                                "value": float(val),
                                "unit": "shares",
                                "source": "sec_edgar_xbrl",
                                "raw_hash": raw_hash,
                                "available_from": end_d,
                                "note": f"from SEC XBRL {shares_key}",
                            }
                        )
            print(f" GLD shares (SEC): {len(rows)} rows from XBRL")
        else:
            print(f" GLD shares (SEC): key '{shares_key}' not found, available: {sorted(facts.keys())[:10]}")
    except Exception as exc:
        print(f" GLD shares (SEC): {type(exc).__name__}: {str(exc)[:80]}")

    # Approach 2: Fallback — current snapshot from yfinance
    if not rows:
        try:
            import yfinance as yf
            t = yf.Ticker("GLD")
            so_val = t.info.get("sharesOutstanding")
            if so_val and so_val > 0:
                today = date.today().isoformat()
                rows.append(
                    {
                        "date": today,
                        "series_id": "GLD_SHARES_OUTSTANDING",
                        "asset": "gld_etf_shares_outstanding",
                        "value": float(so_val),
                        "unit": "shares",
                        "source": "yfinance_gld_info",
                        "available_from": today,
                        "note": "current snapshot only",
                    }
                )
                print(f" GLD shares (yfinance fallback): {so_val/1e6:.1f}M")
        except Exception as exc:
            print(f" GLD shares (yfinance fallback): {type(exc).__name__}: {exc}")

    return rows


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FeatureStatus:
    source: str
    dataset: str
    status: str
    records: int
    warning: str = ""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Collect enhanced external features v2.")
    p.add_argument("--from", dest="from_date", default="2010-01-01")
    p.add_argument("--to", dest="to_date", default=date.today().isoformat())
    p.add_argument("--out-dir", default="data/lake/external_features_v2")
    p.add_argument("--format", default="csv")
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--retries", type=int, default=1)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    norm = out_dir / "normalized"
    norm.mkdir(parents=True, exist_ok=True)
    writer = DataLakeWriter(
        out_dir,
        formats=[f.strip().lower() for f in args.format.split(",") if f.strip()],
    )

    datasets: dict[str, list[dict]] = {
        "macro_enhanced": [],
        "futures_basis": [],
        "etf_proxy": [],
        "lbma_spot": [],
        "gld_shares": [],
        "vn_deposit_rates": [],
        "vn_macro": [],
        "wedding_events": [],
        "policy_events": [],
        "news_events": [],
    }
    statuses: list[FeatureStatus] = []

    # 1. Enhanced FRED
    try:
        fred_rows = collect_enhanced_fred(args.from_date, args.to_date)
        datasets["macro_enhanced"].extend(fred_rows)
        statuses.append(FeatureStatus("fred_json_v2", "macro_enhanced", "ok", len(fred_rows)))
        print(f"FRED enhanced: {len(fred_rows)} rows")
    except Exception as exc:
        statuses.append(FeatureStatus("fred_json_v2", "macro_enhanced", "error", 0, str(exc)))
        print(f"FRED enhanced error: {exc}")

    # 2. GC=F futures
    try:
        fut_rows = collect_gc_futures(args.from_date, args.to_date)
        datasets["futures_basis"].extend(fut_rows)
        statuses.append(FeatureStatus("yfinance_gc_ticker", "futures_basis", "ok", len(fut_rows)))
        print(f"Futures basis: {len(fut_rows)} rows")
    except Exception as exc:
        statuses.append(FeatureStatus("yfinance_gc_ticker", "futures_basis", "error", 0, str(exc)))
        print(f"Futures basis error: {exc}")

    # 3. GLD ETF volume
    try:
        gld_rows = collect_gld_etf(args.from_date, args.to_date)
        datasets["etf_proxy"].extend(gld_rows)
        statuses.append(FeatureStatus("yfinance_gld_ticker", "etf_proxy", "ok", len(gld_rows)))
        print(f"GLD ETF: {len(gld_rows)} rows")
    except Exception as exc:
        statuses.append(FeatureStatus("yfinance_gld_ticker", "etf_proxy", "error", 0, str(exc)))
        print(f"GLD ETF error: {exc}")

    # 3b. LBMA gold spot (London AM fix)
    try:
        lbma_rows = collect_lbma_gold_price()
        datasets["lbma_spot"].extend(lbma_rows)
        statuses.append(
            FeatureStatus("lbma_crawl4ai", "lbma_spot", "ok" if lbma_rows else "empty", len(lbma_rows),
                          warning="" if lbma_rows else "crawl4ai may need network access")
        )
        print(f"LBMA gold fix: {len(lbma_rows)} rows")
    except Exception as exc:
        statuses.append(FeatureStatus("lbma_crawl4ai", "lbma_spot", "error", 0, str(exc)))
        print(f"LBMA gold fix error: {exc}")

    # 3c. GLD shares outstanding — historical (SEC) + current snapshot
    try:
        gld_shares = collect_gld_shares_historical(args.from_date, args.to_date)
        datasets["gld_shares"].extend(gld_shares)
        # Also get current snapshot
        current = collect_gld_shares_outstanding()
        datasets["gld_shares"].extend(current)
        statuses.append(
            FeatureStatus("gld_shares_multi", "gld_shares", "ok" if gld_shares or current else "empty",
                          len(gld_shares) + len(current))
        )
        print(f"GLD shares: {len(gld_shares)} historical + {len(current)} current = {len(gld_shares)+len(current)}")
    except Exception as exc:
        statuses.append(FeatureStatus("gld_shares_multi", "gld_shares", "error", 0, str(exc)))
        print(f"GLD shares error: {exc}")

    # 4. VN deposit rates
    try:
        dep_rows = collect_vietnam_deposit_rates()
        datasets["vn_deposit_rates"].extend(dep_rows)
        statuses.append(
            FeatureStatus(
                "sbv_deposit_json",
                "vn_deposit_rates",
                "ok" if dep_rows else "empty",
                len(dep_rows),
                warning="" if any(r.get("value") for r in dep_rows) else "all values null — parse may need update",
            )
        )
        print(f"VN deposit rates: {len(dep_rows)} rows")
    except Exception as exc:
        statuses.append(FeatureStatus("sbv_deposit_json", "vn_deposit_rates", "error", 0, str(exc)))
        print(f"VN deposit rates error: {exc}")

    # 5. VN macro GSO (Task #2)
    try:
        macro_rows = collect_vn_macro(args.from_date, args.to_date)
        datasets["vn_macro"].extend(macro_rows)
        statuses.append(FeatureStatus("gso_macro_curated", "vn_macro", "ok", len(macro_rows)))
        print(f"VN macro: {len(macro_rows)} rows")
    except Exception as exc:
        statuses.append(FeatureStatus("gso_macro_curated", "vn_macro", "error", 0, str(exc)))
        print(f"VN macro error: {exc}")

    # 6. Wedding season (Task #4)
    try:
        ws_rows = collect_wedding_season(args.from_date, args.to_date)
        datasets["wedding_events"].extend(ws_rows)
        statuses.append(FeatureStatus("rule_based", "wedding_events", "ok", len(ws_rows)))
        print(f"Wedding season: {len(ws_rows)} rows")
    except Exception as exc:
        statuses.append(FeatureStatus("rule_based", "wedding_events", "error", 0, str(exc)))
        print(f"Wedding season error: {exc}")

    # 7. Policy events
    try:
        pol_rows = collect_policy_events()
        datasets["policy_events"].extend(pol_rows)
        statuses.append(FeatureStatus("manual_curation", "policy_events", "ok", len(pol_rows)))
        print(f"Policy events: {len(pol_rows)} rows")
    except Exception as exc:
        statuses.append(FeatureStatus("manual_curation", "policy_events", "error", 0, str(exc)))
        print(f"Policy events error: {exc}")

    # 8. News/sentiment RSS (Task #5)
    try:
        news_rows = collect_news_rss(args.from_date, args.to_date, args.timeout)
        datasets["news_events"].extend(news_rows)
        statuses.append(FeatureStatus("rss_feeds", "news_events", "ok" if news_rows else "empty", len(news_rows)))
        print(f"News RSS: {len(news_rows)} rows")
    except Exception as exc:
        statuses.append(FeatureStatus("rss_feeds", "news_events", "error", 0, str(exc)))
        print(f"News RSS error: {exc}")

    # Write all datasets
    for dataset, rows in datasets.items():
        if rows:
            writer.write_dataset(dataset, rows)

    manifest = {
        "generated_at": date.today().isoformat(),
        "from": args.from_date,
        "to": args.to_date,
        "statuses": [
            {
                "source": s.source,
                "dataset": s.dataset,
                "status": s.status,
                "records": s.records,
                "warning": s.warning,
            }
            for s in statuses
        ],
        "total_records": sum(s.records for s in statuses),
    }
    (out_dir / "manifests" / "enhanced_features_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nDone. Total records: {manifest['total_records']}")
    print(f"Output: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
