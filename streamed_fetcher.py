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
    """Deep network sniffing with custom headers to bypass IP/Bot blocks."""
    page = await context.new_page()
    m3u8_link = None

    # This mirrors exactly what you saw in your screenshot
    def handle_request(request):
        nonlocal m3u8_link
        url = request.url
        if ".m3u8" in url and "strmd.top" in url:
            if "playlist.m3u8" in url:
                m3u8_link = url

    page.on("request", handle_request)

    try:
        # Bypass the automation traps found in DevTools
        await page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")
        
        # Spoofing specific headers that 'lb7.strmd.top' expects
        await page.set_extra_http_headers({
            "Referer": "https://embedsports.top/",
            "Origin": "https://embedsports.top"
        })

        await page.set_viewport_size({"width": 1280, "height": 720})
        print(f"      Probing: {embed_url}")
        
        # Load and wait for the bundle-clappr.js to execute
        await page.goto(embed_url, wait_until="networkidle", timeout=60000)
        
        # Interaction to trigger the 'Initiator' you saw in your screenshot
        await asyncio.sleep(8)
        await page.mouse.click(640, 360) 
        
        # Wait for the handshake (the playlist.m3u8 request)
        await asyncio.sleep(12) 
    except Exception as e:
        print(f"      Timeout or Blocked on this source.")
    finally:
        await page.close()
    
    return m3u8_link

async def main():
    async with async_playwright() as p:
        # Launch with additional arguments to hide the headless nature
        browser = await p.chromium.launch(headless=True, args=[
            '--disable-blink-features=AutomationControlled',
            '--use-fake-ui-for-media-stream'
        ])
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720}
        )

        print("--- Starting Advanced Network Capture ---")
        
        try:
            # Added cache-buster to live.json fetch
            response = await context.request.get(f"{RAW_JSON_URL}?t={int(datetime.now().timestamp())}")
            matches = await response.json()
        except Exception as e:
            print(f"❌ Failed to fetch live.json: {e}")
            return

        m3u_content = ["#EXTM3U", ""]
        count = 0

        for match in matches:
            title = match.get('title', 'Match')
            category = match.get('category', 'Sports').title()
            poster = match.get('poster', '')
            if poster.startswith('/'): poster = f"https://streamed.su{poster}"

            for source in match.get('sources', []):
                provider = source.get('source')
                sid = source.get('id')
                
                print(f"Resolving: {title} ({provider.upper()})...")
                
                api_url = f"{STREAM_API_BASE}/{provider}/{sid}"
                try:
                    api_resp = await context.request.get(api_url)
                    streams = await api_resp.json()
                    if streams:
                        embed_url = streams[0].get('embedUrl')
                        if embed_url:
                            if embed_url.startswith('//'): embed_url = 'https:' + embed_url
                            
                            direct_link = await get_m3u8_from_page(context, embed_url)
                            
                            if direct_link:
                                print(f"      ✅ Link Captured!")
                                m3u_content.append(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{category}",{title} ({provider.upper()})')
                                m3u_content.append(direct_link)
                                count += 1
                                break
                except:
                    continue

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(m3u_content))
        
        print(f"\n✅ Finished: Created playlist with {count} links.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
