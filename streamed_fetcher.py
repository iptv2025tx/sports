#!/usr/bin/env python3

import requests
import json
import os
from datetime import datetime

# Configuration
LIVE_API_URL = "https://streamed.su/api/matches/live"
STREAM_API_BASE = "https://streamed.su/api/stream"
JSON_FILE = 'live.json'
OUTPUT_FILE = 'streamed.m3u'

class StreamFetcher:
    def __init__(self):
        self.session = requests.Session()
        # Using Mobile Safari headers often bypasses data-center blocks
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json',
            'Referer': 'https://streamed.su/',
            'Origin': 'https://streamed.su'
        })

    def fetch_and_save_json(self):
        """Fetches the live JSON from the API and saves it to the repo."""
        print(f"Fetching live data from {LIVE_API_URL}...")
        try:
            # t= timestamp prevents GitHub from receiving a cached empty response
            response = self.session.get(f"{LIVE_API_URL}?t={int(datetime.now().timestamp())}", timeout=20)
            response.raise_for_status()
            data = response.json()
            
            with open(JSON_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            print(f"✅ Saved raw data to {JSON_FILE}")
            return data
        except Exception as e:
            print(f"❌ Failed to fetch JSON: {e}")
            return None

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
        matches = self.fetch_and_save_json()
        if not matches:
            return

        m3u_content = ["#EXTM3U", ""]
        count = 0

        for match in matches:
            title = match.get('title', 'Live Event')
            category = match.get('category', 'Sports').replace('-', ' ').title()
            poster = f"https://streamed.su{match.get('poster', '')}"

            for source in match.get('sources', []):
                provider = source.get('source')
                sid = source.get('id')
                
                real_link = self.get_resolved_url(provider, sid)
                if real_link:
                    # Added group-title for TiviMate groups
                    m3u_content.append(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{category}",{title} ({provider.upper()})')
                    m3u_content.append(real_link)
                    count += 1
                    break 

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(m3u_content))
        
        print(f"✅ Success: Generated {OUTPUT_FILE} with {count} active channels.")

if __name__ == "__main__":
    fetcher = StreamFetcher()
    fetcher.generate_m3u()
