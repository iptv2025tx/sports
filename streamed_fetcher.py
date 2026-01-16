#!/usr/bin/env python3

from curl_cffi import requests
import json
import re
import os
from datetime import datetime

# Configuration
RAW_JSON_URL = "https://raw.githubusercontent.com/BuddyChewChew/sports/refs/heads/main/live.json"
STREAM_API_BASE = "https://streamed.su/api/stream"
OUTPUT_FILE = 'streamed.m3u'

class StreamFetcher:
    def __init__(self):
        # Impersonate Chrome to bypass security on both API and Embed pages
        self.session = requests.Session(impersonate="chrome120")
        self.session.headers.update({
            'Referer': 'https://streamed.su/',
            'Origin': 'https://streamed.su'
        })

    def scrape_direct_link(self, embed_url):
        """Visits the embed page and scrapes the underlying .m3u8 or source link."""
        try:
            # Visit the HTML embed page
            resp = self.session.get(embed_url, timeout=15)
            if resp.status_code == 200:
                html = resp.text
                
                # Look for common stream patterns (m3u8, mp4, etc.) in the Javascript
                # This finds links like: "https://.../index.m3u8"
                found_links = re.findall(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html)
                
                if found_links:
                    # Return the first high-quality stream link found
                    return found_links[0].replace('\\/', '/')
        except Exception as e:
            print(f"      Scrape Error: {e}")
        return None

    def get_resolved_url(self, provider, stream_id):
        """Resolves match ID into an Embed URL, then scrapes it for a direct link."""
        api_url = f"{STREAM_API_BASE}/{provider}/{stream_id}"
        try:
            resp = self.session.get(f"{api_url}?t={int(datetime.now().timestamp())}", timeout=10)
            if resp.status_code == 200:
                streams = resp.json()
                if isinstance(streams, list) and len(streams) > 0:
                    embed_url = streams[0].get('embedUrl')
                    
                    if embed_url:
                        print(f"      Found Embed: {embed_url}")
                        # Now we go deeper to find the actual video file for TiviMate
                        return self.scrape_direct_link(embed_url)
        except Exception:
            pass
        return None

    def generate_m3u(self):
        print(f"Starting deep-link resolution for TiviMate...")
        try:
            response = self.session.get(f"{RAW_JSON_URL}?t={int(datetime.now().timestamp())}")
            response.raise_for_status()
            matches = response.json()
        except Exception as e:
            print(f"❌ Error loading live.json: {e}")
            return

        m3u_content = ["#EXTM3U", ""]
        count = 0

        for match in matches:
            title = match.get('title', 'Live Event')
            category = match.get('category', 'Sports').replace('-', ' ').title()
            poster = match.get('poster', '')
            if poster.startswith('/'):
                poster = f"https://streamed.su{poster}"

            for source in match.get('sources', []):
                provider = source.get('source')
                sid = source.get('id')
                
                print(f"Resolving: {title} ({provider.upper()})...")
                direct_video_link = self.get_resolved_url(provider, sid)
                
                if direct_video_link:
                    m3u_content.append(f'#EXTINF:-1 tvg-logo="{poster}" group-title="{category}",{title} ({provider.upper()})')
                    m3u_content.append(direct_video_link)
                    count += 1
                    break 

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(m3u_content))
        
        print(f"✅ Success: Generated {OUTPUT_FILE} with {count} playable video links.")

if __name__ == "__main__":
    fetcher = StreamFetcher()
    fetcher.generate_m3u()
