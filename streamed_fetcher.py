#!/usr/bin/env python3

import requests
import re
import json
import os

# Configuration
BASE_URL = "https://streamed.su/schedule"
STREAM_API_BASE = "https://streamed.su/api/stream"
OUTPUT_FILE = 'streamed.m3u'

class StreamFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer': 'https://google.com'
        })

    def get_resolved_url(self, provider, stream_id):
        """Resolves the ID into a playable .m3u8 link."""
        try:
            url = f"{STREAM_API_BASE}/{provider}/{stream_id}"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    item = data[0]
                    return item if isinstance(item, str) else item.get('url')
                elif isinstance(data, dict):
                    return data.get('url')
        except:
            pass
        return None

    def generate_m3u(self):
        print(f"Scraping active matches from {BASE_URL}...")
        try:
            response = self.session.get(BASE_URL, timeout=20)
            html = response.text
            
            # This regex looks for the JSON data embedded in the website source
            # which GitHub can't easily be blocked from seeing if it can see the page.
            match_data = re.search(r'id="__NEXT_DATA__" type="application/json">(.*?)</script>', html)
            
            if not match_data:
                print("Could not find match data in HTML. site might be down or blocked.")
                return

            data = json.loads(match_data.group(1))
            # Navigate the Next.js JSON structure to find the matches
            matches = data.get('props', {}).get('pageProps', {}).get('matches', [])
            
        except Exception as e:
            print(f"Critical Error: {e}")
            return

        m3u_content = ["#EXTM3U", ""]
        count = 0

        for match in matches:
            # We focus on things that have sources (meaning they are likely active)
            sources = match.get('sources', [])
            if not sources:
                continue

            title = match.get('title', 'Live Event')
            category = match.get('category', 'Sports').title()
            poster = f"https://streamed.su{match.get('poster', '')}"

            for source in sources:
                provider = source.get('source')
                sid = source.get('id')
                
                real_link = self.get_resolved_url(provider, sid)
                if real_link:
                    m3u_content.append(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{category}",{title} ({provider.upper()})')
                    m3u_content.append(real_link)
                    count += 1
                    break 

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(m3u_content))
        
        print(f"✅ Success: Generated {OUTPUT_FILE} with {count} channels.")

if __name__ == "__main__":
    fetcher = StreamFetcher()
    fetcher.generate_m3u()
