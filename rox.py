import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.exceptions import RequestException
import logging

BASE_URL = "https://roxiestreams.live"
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_DUMMY_CHANNELS.xml.gz"

# Integrated Mapping
TV_INFO = {
    "ppv": ("PPV.EVENTS.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/ppv2.png?raw=true", "PPV Events"),
    "soccer": ("Soccer.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/football.png?raw=true", "Soccer"),
    "ufc": ("UFC.Fight.Pass.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/mma.png?raw=true", "Combat Sports"),
    "fighting": ("Combat.Sports.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/boxing.png?raw=true", "Combat Sports"),
    "nfl": ("Football.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/nfl.png?raw=true", "Football"),
    "nhl": ("NHL.Hockey.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/hockey.png?raw=true", "Hockey"),
    "f1": ("Racing.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/f1.png?raw=true", "Motorsports"),
    "motorsports": ("Racing.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/f1.png?raw=true", "Motorsports"),
    "nba": ("NBA.Basketball.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/nba.png?raw=true", "Basketball"),
    "mlb": ("MLB.Baseball.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/baseball.png?raw=true", "Baseball")
}

DEFAULT_LOGO = "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/default.png?raw=true"
DEFAULT_GROUP = "General Sports"
DISCOVERY_KEYWORDS = list(TV_INFO.keys()) + ['streams']

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': BASE_URL
})

M3U8_REGEX = re.compile(r'https?://[^\s"\'<>`]+\.m3u8')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_tv_info(url, title=""):
    combined = (url + title).lower()
    for key, (epg_id, logo, group) in TV_INFO.items():
        if key in combined: return epg_id, logo, group
    return "Sports.Rox.us", DEFAULT_LOGO, DEFAULT_GROUP

def discover_sections(base_url):
    """Finds top-level categories and ensures major ones aren't missed."""
    sections_found = [
        (f"{BASE_URL}/nfl", "NFL"),
        (f"{BASE_URL}/mlb", "MLB"),
        (f"{BASE_URL}/nba", "NBA"),
        (f"{BASE_URL}/nhl", "NHL"),
        (f"{BASE_URL}/soccer", "Soccer"),
        (f"{BASE_URL}/fighting", "Fighting"),
        (f"{BASE_URL}/motorsports", "Motorsports")
    ]
    try:
        resp = SESSION.get(base_url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        existing_urls = {s[0] for s in sections_found}
        for a in soup.find_all('a', href=True):
            abs_url = urljoin(base_url, a['href'])
            if abs_url.startswith(BASE_URL) and any(k in abs_url.lower() for k in DISCOVERY_KEYWORDS):
                if abs_url not in existing_urls:
                    sections_found.append((abs_url, a.get_text(strip=True)))
                    existing_urls.add(abs_url)
    except: pass
    return sections_found

def discover_event_links(section_url):
    """Checks for the eventsTable and follows stream links."""
    events = set()
    try:
        resp = SESSION.get(section_url, timeout=10)
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Target the specific table you identified
        table = soup.find('table', id='eventsTable')
        links = table.find_all('a', href=True) if table else soup.find_all('a', href=True)
        
        for a in links:
            href = a['href']
            title = a.get_text(strip=True)
            if '/stream/' in href or any(s in href.lower() for s in TV_INFO.keys()):
                events.add((urljoin(section_url, href), title))
    except: pass
    return events

def extract_m3u8_links(page_url):
    """Scrapes page and nested iframes for stream links."""
    links = set()
    try:
        resp = SESSION.get(page_url, timeout=10)
        links.update(M3U8_REGEX.findall(resp.text))
        
        # Check iframes (NFL streams often hide here)
        soup = BeautifulSoup(resp.text, 'html.parser')
        for iframe in soup.find_all('iframe', src=True):
            if_url = urljoin(page_url, iframe['src'])
            if 'roxiestreams' in if_url or 'embed' in if_url:
                if_resp = SESSION.get(if_url, timeout=5)
                links.update(M3U8_REGEX.findall(if_resp.text))
    except: pass
    return links

def main():
    playlist = [f'#EXTM3U x-tvg-url="{EPG_URL}"']
    sections = discover_sections(BASE_URL)
    seen_links = set()
    title_tracker = {}

    for section_url, section_title in sections:
        logging.info(f"Scanning Section: {section_title}")
        events = discover_event_links(section_url)
        
        for event_url, event_title in events:
            m3u8_links = extract_m3u8_links(event_url)
            for link in m3u8_links:
                if link in seen_links: continue
                
                try:
                    if SESSION.head(link, timeout=5).status_code == 200:
                        tv_id, logo, group = get_tv_info(event_url, event_title)
                        title_tracker[event_title] = title_tracker.get(event_title, 0) + 1
                        count = title_tracker[event_title]
                        name = event_title if count == 1 else f"{event_title} (Mirror {count-1})"
                        
                        playlist.append(f'#EXTINF:-1 tvg-id="{tv_id}" tvg-logo="{logo}" group-title="{group}",{name}')
                        playlist.append(link)
                        seen_links.add(link)
                        logging.info(f"  > Added: {name}")
                except: continue

    with open("Roxiestreams.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(playlist))

if __name__ == "__main__":
    main()
