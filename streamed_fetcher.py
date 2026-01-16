#!/usr/bin/env python3

import requests
import os
from datetime import datetime, timezone

# Configuration
# Note: Streamed.su is the current primary domain for this service
BASE_URL = "https://streamed.su/api/matches/all"
STREAM_API = "https://streamed.su/api/stream"
OUTPUT_FILE = 'streamed.m3u'

class StreamFetcher:
    def __init__(self):
        self.session = requests.Session()
        # Mimicking an iPhone/Safari browser often bypasses basic bot checks
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            'Accept': 'application/json',
            'Origin': 'https://streamed.su',
            'Referer': 'https://streamed.su/'
        })

    def get_live_link(self, source_type, source_id):
        """Resolves the JSON to a direct video link."""
        try:
            url = f"{STREAM_API}/{source_type}/{source_id}"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get('url')
                return data.get('url')
        except:
            pass
        return None

    def generate_m3u(self):
        print("Fetching currently LIVE matches...")
        try:
            # We add a cache-buster timestamp to avoid getting 'old' cached empty data
            response = self.session.get(f"{BASE_URL}?t={int(datetime.now().timestamp())}", timeout=20)
            response.raise_for_status()
            matches = response.json()
        except Exception as e:
            print(f"Connection failed: {e}")
            return

        m3u_content = ["#EXTM3U", ""]
        live_count = 0
        now = datetime.now(timezone.utc)

        for match in matches:
            # Skip if match has no date (invalid)
            if not match.get('date'):
                continue
                
            event_time = datetime.fromtimestamp(match['date'] / 1000, tz=timezone.utc)
            
            # STRICT "LIVE NOW" FILTER:
            # Match must have started already (within last 4 hours) 
            # OR is starting in the next 5 minutes.
            hours_diff = (event_time - now).total_seconds() / 3600
            
            if -4 <= hours_diff <= 0.08: # 0.08 hours is approx 5 minutes
                category = match.get('category', 'Live').title()
                poster = f"https://streamed.su{match.get('poster', '')}"
                
                for source in match.get('sources', []):
                    s_type = source.get('source')
                    s_id = source.get('id')
                    
                    real_url = self.get_live_link(s_type, s_id)
                    if real_url:
                        display_name = f"LIVE: {match['title']} ({s_type.upper()})"
                        m3u_content.append(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{category}",{display_name}')
                        m3u_content.append(real_url)
                        live_count += 1
                        break # Only take the first working source per match

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(m3u_content))
        
        print(f"✅ Success: Generated {OUTPUT_FILE} with {live_count} currently LIVE matches.")

if __name__ == "__main__":
    fetcher = StreamFetcher()
    fetcher.generate_m3u()
