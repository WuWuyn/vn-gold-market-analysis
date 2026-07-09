#!/usr/bin/env python3
"""Deep-crawl SJC gold page and Vietcombank FX page with crawl4ai."""
import asyncio
from crawl4ai import AsyncWebCrawler, CacheMode


async def main():
    async with AsyncWebCrawler(headless=True, cache_mode=CacheMode.BYPASS) as crawler:
        # --- SJC Gold Price ---
        print("=== SJC GOLD PRICE ===")
        r = await crawler.arun(
            url="https://sjc.com.vn/bieu-do-gia-vang",
            word_count_threshold=1,
            page_timeout=20_000,
            js_code=[
                "() => { return { title: document.title, url: document.location.href, body_len: document.body.innerText.length }; }"
            ],
            css_selector="table",  # grab all tables
        )
        text = r.markdown or ""
        # Extract price table lines
        lines = [l.rstrip() for l in text.split('\n') if l.strip()]
        for l in lines:
            if any(k in l for k in ['Mua', 'Bán', 'nguyên đán', 'chỉ', 'lượng', 'SJC', 'tael', 'Chi']):
                print(f"  {l[:150]}")
        print(f"\n  Full length: {len(text)} chars")
        # Print the section around "BẢNG GIÁ VÀNG"
        for i, l in enumerate(lines):
            if 'BẢNG GIÁ VÀNG' in l or 'BẢNG' in l and 'VÀNG' in l:
                for j in range(max(0, i-2), min(len(lines), i+25)):
                    print(f"  [{j}] {lines[j][:160]}")
                break

        # --- Vietcombank FX ---
        print("\n=== VIETCOMBANK FX ===")
        r2 = await crawler.arun(
            url="https://www.vietcombank.com.vn/vi-VN/KHCN/Cong-cu-Tien-ich/Ty-gia",
            word_count_threshold=1,
            page_timeout=20_000,
        )
        text2 = r2.markdown or ""
        lines2 = [l.rstrip() for l in text2.split('\n') if l.strip()]
        for i, l in enumerate(lines2):
            if 'USD' in l or 'VND' in l:
                print(f"  [{i}] {l[:160]}")
        # Extract the rate table
        for i, l in enumerate(lines2):
            if 'Mua tiền mặt' in l or 'Tỷ giá' in l:
                for j in range(max(0, i), min(len(lines2), i+30)):
                    print(f"  [{j}] {lines2[j][:160]}")
                break


if __name__ == "__main__":
    asyncio.run(main())
