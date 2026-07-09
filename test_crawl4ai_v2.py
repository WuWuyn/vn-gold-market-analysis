#!/usr/bin/env python3
"""Test crawl4ai to extract structured data from Vietcombank and SBV."""
import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode


async def test():
    targets = [
        {
            "name": "Vietcombank_FX",
            "url": "https://www.vietcombank.com.vn/vi-VN/KHCN/Cong-cu-Tien-ich/Ty-gia",
            "extract": True,
        },
        {
            "name": "SBV_try_alt",
            "url": "https://www.sbv.gov.vn/ty-gia",
            "extract": True,
        },
        {
            "name": "SJC_gold",
            "url": "https://sjc.com.vn/bieu-do-gia-vang",
            "extract": False,
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
                    word_count_threshold=1,
                    wait_for="css:body",
                    page_timeout=30_000,
                    **(dict(extract_schema={"rates": "list", "_default": "markdown"}) if t["extract"] else {}),
                )
                text = result.markdown or result.html or ""
                print(f"  Success: {result.success}")
                print(f"  Length: {len(text)} chars")
                # Find any VND/USD/rate-like numbers
                import re
                lines = text.split('\n')
                for line in lines:
                    if any(kw in line.upper() for kw in ['MUA', 'BÁN', 'USD', 'VND', 'RATE', 'GIÁ']):
                        print(f"  LINE: {line[:120]}")
            except Exception as e:
                print(f"  ERROR: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test())
