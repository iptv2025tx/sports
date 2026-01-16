#!/usr/bin/env python3

import requests
import re
import os
from datetime import datetime, timezone

# Configuration
SOURCE_URL = "https://streamed.pk/"
STREAM_API_BASE = "https://streamed.pk/api/stream"
OUTPUT_FILE = 'streamed.m3u'

class StreamFetcher:
    def __init__(self):
        self.session = requests.Session()
        # Using a very high-quality Browser User-Agent
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Referer': 'https://google.com',
            'Accept-Language': 'en-US,en;q=0.5'
        })

    def get_real_m3u8(self, source_type, source_id):
        """Attempts to resolve the actual video file link."""
        try:
            url = f"{STREAM_API_BASE}/{source_type}/{source_id}"
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return data[0].get('url') or data[0].get('link')
                elif isinstance(data, dict):
                    return data.get('url') or data.get('link')
        except:
            pass
        return None

    def generate_m3u(self):
        print(f"Connecting to {SOURCE_URL}...")
        try:
            response = self.session.get(SOURCE_URL, timeout=20)
            response.raise_for_status()
            html = response.text
        except Exception as e:
            print(f"Failed to connect: {e}")
            return

        # Regex to find match data inside the HTML 
        # This targets the internal data structures used by the site
        matches = re.findall(r'data-match=\'(.*?)\'', html)
        
        if not matches:
            # Plan B: Try to find raw stream IDs in the text
            print("Direct data not found, attempting deep scan...")
            matches = re.findall(r'href="/watch/(.*?)"', html)

        m3u_content = ["#EXTM3U", ""]
        count = 0

        for match_id in set(matches):
            # Clean up match ID
            match_id = match_id.strip()
            
            # For simplicity in this scraper, we assume standard sports categorization
            # We try to resolve at least one working source for the match
            # Note: streamed.pk usually uses 'admin', 'charlie', or 'echo' as sources
            for provider in ['admin', 'charlie', 'echo']:
                real_url = self.get_real_m3u8(provider, match_id)
                if real_url:
                    title = match_id.replace('-', ' ').title()
                    m3u_content.append(f'#EXTINF:-1 group-title="Live Sports",{title} [{provider.upper()}]')
                    m3u_content.append(real_url)
                    count += 1
                    break # Move to next match once one link is found

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(m3u_content))
        
        print(f"✅ Success: Generated {OUTPUT_FILE} with {count} active channels.")

if __name__ == "__main__":
    fetcher = StreamFetcher()
    fetcher.generate_m3u()
