import asyncio
from playwright.async_api import async_playwright
import json

# Run this on your PC, NOT on GitHub Actions
async def capture_local():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Headless=False helps bypass blocks
        page = await browser.new_page()
        
        m3u8_links = []
        page.on("request", lambda req: m3u8_links.append(req.url) if ".m3u8" in req.url else None)

        print("Go to the match page in the browser that just opened...")
        await page.goto("https://streamed.su", wait_until="networkidle")
        
        # Keep browser open for 60 seconds while you click around
        await asyncio.sleep(60) 
        
        with open("captured_links.txt", "w") as f:
            for link in m3u8_links:
                f.write(link + "\n")
        
        print(f"Captured {len(m3u8_links)} potential links to captured_links.txt")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_local())
