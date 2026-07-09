#!/usr/bin/env python3
"""Test crawl4ai against blocked endpoints: SBV FX, FRED, Vietcombank."""
import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode


async def test():
    targets = [
        {
            "name": "FRED_DFII10",
            "url": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10&cosd=2024-01-01&coed=2024-06-30",
            "expect": "DFII10",
        },
        {
            "name": "SBV_FX",
            "url": "https://www.sbv.gov.vn/vi/ty-gia",
            "expect": "VND",
        },
        {
            "name": "Vietcombank_FX",
            "url": "https://www.vietcombank.com.vn/vi-VN/KHCN/Cong-cu-Tien-ich/Ty-gia",
            "expect": "USD",
        },
    ]

    async with AsyncWebCrawler(
        browser_type="chromium",
        headless=True,
        cache_mode=CacheMode.BYPASS,
    ) as crawler:
        for t in targets:
            print(f"\n--- {t['name']} ---")
            try:
                result = await crawler.arun(
                    url=t["url"],
                    word_count_threshold=5,
                    wait_for="css:body",
                    page_timeout=30_000,
                )
                text = result.markdown or result.html or ""
                has = t["expect"].upper() in text.upper()
                print(f"  Status: {'OK' if result.success else 'FAIL'}")
                print(f"  Found '{t['expect']}': {has}")
                print(f"  Length: {len(text)} chars")
                print(f"  Preview: {text[:200]}")
            except Exception as e:
                print(f"  ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test())
