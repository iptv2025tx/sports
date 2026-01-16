import asyncio
from playwright.async_api import async_playwright
import json
import re
from datetime import datetime

# Configuration
RAW_JSON_URL = "https://raw.githubusercontent.com/BuddyChewChew/sports/refs/heads/main/live.json"
STREAM_API_BASE = "https://streamed.su/api/stream"
OUTPUT_FILE = 'streamed.m3u'

async def get_m3u8_from_page(page, embed_url):
    """Wait for the page to load and look for any .m3u8 network requests."""
    m3u8_link = None
    
    # This listener catches the link as it's requested by the player
    def handle_request(request):
        nonlocal m3u8_link
        if ".m3u8" in request.url and "strmd.top" in request.url:
            m3u8_link = request.url

    page.on("request", handle_request)
    
    try:
        await page.goto(embed_url, wait_until="networkidle", timeout=30000)
        # Give the player 5 extra seconds to "handshake" and find the stream
        await asyncio.sleep(5)
    except:
        pass
    
    return m3u8_link

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36")
        page = await context.new_page()

        # Fetch the match list
        async with context.request.get(RAW_JSON_URL) as response:
            matches = await response.json()

        m3u_content = ["#EXTM3U", ""]
        count = 0

        for match in matches:
            title = match.get('title', 'Live Match')
            category = match.get('category', 'Sports').title()
            poster = f"https://streamed.su{match.get('poster')}" if match.get('poster', '').startswith('/') else match.get('poster', '')

            for source in match.get('sources', []):
                print(f"Resolving: {title}...")
                
                # Get the embed URL from the API
                api_url = f"{STREAM_API_BASE}/{source.get('source')}/{source.get('id')}"
                async with context.request.get(api_url) as api_resp:
                    streams = await api_resp.json()
                    if streams and len(streams) > 0:
                        embed_url = streams[0].get('embedUrl')
                        if embed_url:
                            if embed_url.startswith('//'): embed_url = 'https:' + embed_url
                            
                            # Deep scrape using the browser
                            direct_link = await get_m3u8_from_page(page, embed_url)
                            
                            if direct_link:
                                m3u_content.append(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{category}",{title}')
                                m3u_content.append(direct_link)
                                count += 1
                                print(f"  ✅ Found: {direct_link[:50]}...")
                                break

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(m3u_content))
        
        print(f"\n✅ Finished: {count} links added to {OUTPUT_FILE}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
