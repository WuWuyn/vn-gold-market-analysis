#!/usr/bin/env python3
"""Try to get Vietcombank FX rates via crawl4ai with raw HTML + JS execution."""
import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode


async def main():
    async with AsyncWebCrawler(headless=True, cache_mode=CacheMode.BYPASS) as crawler:
        r = await crawler.arun(
            url="https://www.vietcombank.com.vn/vi-VN/KHCN/Cong-cu-Tien-ich/Ty-gia",
            page_timeout=20_000,
            js_code="() => document.body.innerText",
            wait_for="css:table, .rate, .tygia",
            # Also try to get the raw HTML and look for JSON data embedded in page
        )
        # Check html
        html = r.html or ""
        markdown = r.markdown or ""
        print(f"HTML len: {len(html)}, Markdown len: {len(markdown)}")
        # Look for JSON blobs or data attributes
        for kw in ["Mua tiền mặt", "USD", "exchangeRate", "rateTable", "tyGia", "__NEXT_DATA__"]:
            idx = html.find(kw)
            if idx >= 0:
                print(f"Found '{kw}' at {idx}: {html[max(0,idx-50):idx+200]}")
            else:
                print(f"'{kw}' NOT in HTML")
        # Print raw text portion that has rates
        lines = markdown.split('\n')
        for i, l in enumerate(lines):
            if any(k in l for k in ['Mua', 'Bán', 'USD', '#']):

