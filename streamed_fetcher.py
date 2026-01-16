#!/usr/bin/env python3

import requests
import os
from datetime import datetime, timezone

# Configuration
# Streamed.su is the most stable domain for their live API in 2026
LIVE_API_URL = "https://streamed.su/api/matches/live"
STREAM_API_BASE = "https://streamed.su/api/stream"
OUTPUT_FILE = 'streamed.m3u'

class StreamFetcher:
    def __init__(self):
        self.session = requests.Session()
        # High-authority headers to mimic a browser and bypass bot detection
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://streamed.su',
            'Referer': 'https://streamed.su/watch',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        })

    def get_resolved_url(self, provider, stream_id):
        """Resolves the internal ID into a direct, playable m3u8 stream link."""
        try:
            url = f"{STREAM_API_BASE}/{provider}/{stream_id}"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                # The API usually returns a list of source objects or a direct 'url' key
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get('url') or data[0].get('link')
                return data.get('url') or data.get('link')
        except Exception as e:
            print(f"Error resolving stream {stream_id}: {e}")
        return None

    def generate_m3u(self):
        print(f"Polling LIVE matches from: {LIVE_API_URL}")
        try:
            # Cache buster helps ensure GitHub doesn't serve an old version of the API response
            response = self.session.get(f"{LIVE_API_URL}?t={int(datetime.now().timestamp())}", timeout=20)
            response.raise_for_status()
            live_matches = response.json()
        except Exception as e:
            print(f"Failed to fetch live data: {e}")
            return

        m3u_content = ["#EXTM3U", ""]
        channel_count = 0

        for match in live_matches:
            title = match.get('title', 'Live Event')
            # Categorize by sport
            category = match.get('category', 'Sports').replace('-', ' ').title()
            poster = f"https://streamed.su{match.get('poster', '')}"

            for source in match.get('sources', []):
                provider = source.get('source')
                stream_id = source.get('id')
                
                if not provider or not stream_id: continue

                # Important: This step gets the actual .m3u8 link TiviMate needs
                playable_url = self.get_resolved_url(provider, stream_id)
                
                if playable_url:
                    # Clean title for TiviMate display
                    display_name = f"{title} [{provider.upper()}]"
                    m3u_content.append(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{category}",{display_name}')
                    m3u_content.append(playable_url)
                    channel_count += 1
                    # Only one working link per match to prevent duplicates
                    break

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(m3u_content))
        
        print(f"✅ Success: Generated {OUTPUT_FILE} with {channel_count} live channels.")

if __name__ == "__main__":
    fetcher = StreamFetcher()
    fetcher.generate_m3u()
