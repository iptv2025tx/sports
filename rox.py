import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging

# Integrated Settings & Constants
BASE_URL = "https://roxiestreams.live"
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_DUMMY_CHANNELS.xml.gz"

# Explicit Category URLs as requested
CATEGORIES = [
    f"{BASE_URL}/nfl",
    f"{BASE_URL}/soccer",
    f"{BASE_URL}/mlb",
    f"{BASE_URL}/nba",
    f"{BASE_URL}/nhl",
    f"{BASE_URL}/fighting",
    f"{BASE_URL}/motorsports"
]

TV_INFO = {
    "ppv": ("PPV.EVENTS.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/ppv2.png?raw=true", "PPV Events"),
    "soccer": ("Soccer.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/football.png?raw=true", "Soccer"),
    "ufc": ("UFC.Fight.Pass.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/mma.png?raw=true", "Combat Sports"),
    "fighting": ("Combat.Sports.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/boxing.png?raw=true", "Combat Sports"),
    "nfl": ("Football.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/nfl.png?raw=true", "Football"),
    "nhl": ("NHL.Hockey.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/nhl.png?raw=true", "Hockey"),
    "f1": ("Racing.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/f1.png?raw=true", "Motorsports"),
    "motorsports": ("Racing.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/f1.png?raw=true", "Motorsports"),
    "wwe": ("PPV.EVENTS.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/wwe.png?raw=true", "Wrestling"),
    "nba": ("NBA.Basketball.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/nba.png?raw=true", "Basketball"),
    "mlb": ("MLB.Baseball.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/baseball.png?raw=true", "Baseball")
}

DEFAULT_LOGO = "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/default.png?raw=true"
DEFAULT_GROUP = "General Sports"

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': BASE_URL
})

M3U8_REGEX = re.compile(r'https?://[^\s"\'<>`]+\.m3u8')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_tv_info(url, title=""):
    combined_text = (url + title).lower()
    for key, (epg_id, logo, group) in TV_INFO.items():
        if key in combined_text:
            return epg_id, logo, group
    return "Sports.Rox.us", DEFAULT_LOGO, DEFAULT_GROUP

def extract_event_links(cat_url):
    events = set()
    try:
        resp = SESSION.get(cat_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            title = a_tag.get_text(strip=True)
            if href and title and len(title) > 3:
                abs_url = urljoin(BASE_URL, href)
                # Ensure we are linking to actual event pages, not categories
                if abs_url.startswith(BASE_URL) and not any(cat in abs_url.lower() for cat in ['/nfl', '/nba', '/mlb', '/nhl', '/soccer']):
                    events.add((abs_url, title))
    except Exception as e:
        logging.error(f"Error reading category {cat_url}: {e}")
    return events

def extract_m3u8_links(page_url):
    links = set()
    try:
        resp = SESSION.get(page_url, timeout=10)
        resp.raise_for_status()
        links.update(M3U8_REGEX.findall(resp.text))
        
        # Hidden player files
        scripts = re.findall(r'file:\s*["\'](.*?\.m3u8.*?)["\']', resp.text)
        links.update(scripts)
    except Exception:
        pass
    return links

def check_stream_status(m3u8_url):
    try:
        resp = SESSION.get(m3u8_url, timeout=5, stream=True)
        return resp.status_code == 200
    except Exception:
        return False

def main():
    playlist_lines = [f'#EXTM3U x-tvg-url="{EPG_URL}"']
    seen_links = set()
    title_tracker = {}

    for cat_url in CATEGORIES:
        logging.info(f"Scraping: {cat_url}")
        events = extract_event_links(cat_url)
        
        for event_url, event_title in events:
            tv_id, logo, group_name = get_tv_info(event_url, event_title)
            m3u8_links = extract_m3u8_links(event_url)
            
            for link in m3u8_links:
                if link in seen_links: continue
                
                if check_stream_status(link):
                    title_tracker[event_title] = title_tracker.get(event_title, 0) + 1
                    count = title_tracker[event_title]
                    display_name = event_title if count == 1 else f"{event_title} (Mirror {count-1})"
                    
                    playlist_lines.append(f'#EXTINF:-1 tvg-id="{tv_id}" tvg-logo="{logo}" group-title="{group_name}",{display_name}')
                    playlist_lines.append(link)
                    seen_links.add(link)

    with open("Roxiestreams.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(playlist_lines))
    logging.info(f"Finished! Found {len(seen_links)} live streams.")

if __name__ == "__main__":
    main()
