#!/usr/bin/env python3

import requests
import os
import json
from datetime import datetime, timezone

# Configuration
LIVE_API_URL = "https://streamed.su/api/matches/live"
STREAM_API_BASE = "https://streamed.su/api/stream"
OUTPUT_FILE = 'streamed.m3u'

class StreamFetcher:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Origin': 'https://streamed.su',
            'Referer': 'https://streamed.su/watch'
        })

    def get_resolved_url(self, provider, stream_id):
        """Resolves internal IDs into playable links by handling list/dict responses."""
        try:
            url = f"{STREAM_API_BASE}/{provider}/{stream_id}"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                
                # Logic to handle the 'list' error found in your previous run
                if isinstance(data, list) and len(data) > 0:
                    item = data[0]
                    # Check if the list contains a string (direct link) or an object
                    return item if isinstance(item, str) else item.get('url') or item.get('link')
                elif isinstance(data, dict):
                    return data.get('url') or data.get('link')
        except:
            pass
        return None

    def generate_m3u(self):
        print(f"Fetching live matches...")
        try:
            response = self.session.get(f"{LIVE_API_URL}?t={int(datetime.now().timestamp())}", timeout=20)
            response.raise_for_status()
            matches = response.json()
        except Exception as e:
            print(f"Failed to fetch live matches: {e}")
            return

        m3u_content = ["#EXTM3U", ""]
        count = 0

        for match in matches:
            # Extract data from the format provided in your live.json
            title = match.get('title', 'Unknown Event')
            category = match.get('category', 'Sports').title()
            poster = f"https://streamed.su{match.get('poster', '')}"

            for source in match.get('sources', []):
                provider = source.get('source')
                sid = source.get('id')
                
                real_link = self.get_resolved_url(provider, sid)
                if real_link:
                    # Clean title and format for TiviMate
                    m3u_content.append(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{category}",{title} ({provider.upper()})')
                    m3u_content.append(real_link)
                    count += 1
                    break # Take the first working source for each match

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(m3u_content))
        
        print(f"✅ Success: Generated {OUTPUT_FILE} with {count} live channels.")

if __name__ == "__main__":
    fetcher = StreamFetcher()
    fetcher.generate_m3u()
