import asyncio
from playwright.async_api import async_playwright
import json
import os
from datetime import datetime

# Configuration
RAW_JSON_URL = "https://raw.githubusercontent.com/BuddyChewChew/sports/refs/heads/main/live.json"
STREAM_API_BASE = "https://streamed.su/api/stream"
OUTPUT_FILE = 'streamed.m3u'

async def get_m3u8_from_page(context, embed_url):
    """Acts like a human opening DevTools to catch the playlist.m3u8."""
    page = await context.new_page()
    m3u8_link = None

    # Listen for the exact link pattern from your screenshot
    def handle_request(request):
        nonlocal m3u8_link
        url = request.url
        if ".m3u8" in url and "strmd.top" in url:
            if "playlist.m3u8" in url or "master.m3u8" in url:
                m3u8_link = url

    page.on("request", handle_request)

    try:
        # 1. Bypass the 'abort-on-property-read' traps
        await page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")
        
        # 2. Set headers to match your browser's 'Initiator' environment
        await page.set_extra_http_headers({
            "Referer": "https://embedsports.top/",
            "Origin": "https://embedsports.top"
        })

        await page.set_viewport_size({"width": 1920, "height": 1080})
        print(f"      Probing: {embed_url}")
        
        # 3. Use 'networkidle' to ensure bundle-clappr.js is fully loaded
        await page.goto(embed_url, wait_until="networkidle", timeout=60000)
        
        # 4. Human-like delay and multi-click to break 'autoplay' blocks
        await asyncio.sleep(10) 
        await page.mouse.click(960, 540) # Click center
        await asyncio.sleep(2)
        await page.mouse.click(960, 540) # Double click to be sure
        
        # 5. Wait for the 'playlist.m3u8' to appear in the network tab
        await asyncio.sleep(15) 
    except Exception:
        pass
    finally:
        await page.close()
    
    return m3u8_link

async def main():
    async with async_playwright() as p:
        # Launch with flags to look like a standard desktop browser
        browser = await p.chromium.launch(headless=True, args=[
            '--disable-blink-features=AutomationControlled'
        ])
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )

        print("--- Resolving Dynamic Streams (Network-Intercept Mode) ---")
        
        response = await context.request.get(f"{RAW_JSON_URL}?t={int(datetime.now().timestamp())}")
        matches = await response.json()

        m3u_content = ["#EXTM3U", ""]
        count = 0

        for match in matches:
            title = match.get('title', 'Live Match')
            category = match.get('category', 'Sports').title()
            poster = match.get('poster', '')
            if poster.startswith('/'): poster = f"https://streamed.su{poster}"

            for source in match.get('sources', []):
                provider = source.get('source')
                sid = source.get('id')
                
                print(f"Checking: {title} ({provider.upper()})...")
                
                api_url = f"{STREAM_API_BASE}/{provider}/{sid}"
                try:
                    api_resp = await context.request.get(api_url)
                    streams = await api_resp.json()
                    if streams and streams[0].get('embedUrl'):
                        embed_url = streams[0]['embedUrl']
                        if embed_url.startswith('//'): embed_url = 'https:' + embed_url
                        
                        # Catch the link that only appears after a click
                        direct_link = await get_m3u8_from_page(context, embed_url)
                        
                        if direct_link:
                            print(f"      ✅ Captured Stream!")
                            m3u_content.append(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{category}",{title} ({provider.upper()})')
                            m3u_content.append(direct_link)
                            count += 1
                            break
                except:
                    continue

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(m3u_content))
        
        print(f"\n✅ Finished! Created playlist with {count} active links.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
