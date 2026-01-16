#!/usr/bin/env python3

import requests
import json
import os
from datetime import datetime

# Configuration
# We pull from YOUR raw GitHub link because that is guaranteed to have data
RAW_JSON_URL = "https://raw.githubusercontent.com/BuddyChewChew/sports/refs/heads/main/live.json"
STREAM_API_BASE = "https://streamed.su/api/stream"
OUTPUT_FILE = 'streamed.m3u'

class StreamFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Referer': 'https://streamed.su/watch'
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
        print(f"Reading live data from your repository...")
        try:
            # Fetch the JSON that YOU successfully saved to your repo
            response = self.session.get(f"{RAW_JSON_URL}?t={int(datetime.now().timestamp())}")
            response.raise_for_status()
            matches = response.json()
            
            if not matches or len(matches) == 0:
                print("⚠️ The live.json in your repo is currently empty.")
                return

        except Exception as e:
            print(f"❌ Error reading live.json: {e}")
            return

        m3u_content = ["#EXTM3U", ""]
        count = 0

        for match in matches:
            title = match.get('title', 'Live Event')
            # Grouping logic for TiviMate
            category = match.get('category', 'Sports').replace('-', ' ').title()
            poster = f"https://streamed.su{match.get('poster', '')}"

            for source in match.get('sources', []):
                provider = source.get('source')
                sid = source.get('id')
                
                print(f"Resolving: {title}...")
                real_link = self.get_resolved_url(provider, sid)
                
                if real_link:
                    # Formatting with group-title for TiviMate organization
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
