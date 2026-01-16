import requests
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.exceptions import RequestException
import logging

BASE_URL = "https://roxiestreams.live"
# Your specific EPG URL integrated into the script
EPG_URL = "https://epgshare01.online/epgshare01/epg_ripper_DUMMY_CHANNELS.xml.gz"

TV_INFO = {
    "ppv": ("PPV.EVENTS.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/ppv2.png?raw=true"),
    "soccer": ("Soccer.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/football.png?raw=true"),
    "ufc": ("UFC.Fight.Pass.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/mma.png?raw=true"),
    "fighting": ("PPV.EVENTS.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/boxing.png?raw=true"),
    "nfl": ("Football.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/nfl.png?raw=true"),
    "f1": ("Racing.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/f1.png?raw=true"),
    "motorsports": ("Racing.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/f1.png?raw=true"),
    "wwe": ("PPV.EVENTS.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/wwe.png?raw=true"),
    "nba": ("NBA.Basketball.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/nba.png?raw=true"),
    "mlb": ("MLB.Baseball.Dummy.us", "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/baseball.png?raw=true")
}

DEFAULT_LOGO = "https://github.com/BuddyChewChew/sports/blob/main/sports%20logos/ppv2.png?raw=true"
DISCOVERY_KEYWORDS = list(TV_INFO.keys()) + ['streams']
SECTION_BLOCKLIST = ['olympia']

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': BASE_URL
})

M3U8_REGEX = re.compile(r'https?://[^\s"\'<>`]+\.m3u8')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_tv_info(url, title=""):
    combined_text = (url + title).lower()
    for key, value in TV_INFO.items():
        if key in combined_text:
            return value
    return ("Sports.Rox.us", DEFAULT_LOGO)

def discover_sections(base_url):
    sections_found = []
    try:
        resp = SESSION.get(base_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        discovered_urls = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            title = a_tag.get_text(strip=True)
            if not href or href.startswith(('#', 'javascript:', 'mailto:')) or not title:
                continue
            abs_url = urljoin(base_url, href)
            if any(blocked in abs_url.lower() for blocked in SECTION_BLOCKLIST):
                continue
            if (urlparse(abs_url).netloc == urlparse(base_url).netloc and
                    any(keyword in abs_url.lower() for keyword in DISCOVERY_KEYWORDS)):
                if abs_url not in discovered_urls:
                    discovered_urls.add(abs_url)
                    sections_found.append((abs_url, title))
    except RequestException as e:
        logging.error(f"Failed discovery: {e}")
    return sections_found

def discover_event_links(section_url):
    events = set()
    try:
        resp = SESSION.get(section_url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')
        event_table = soup.find('table', id='eventsTable') 
        if event_table:
            for a_tag in event_table.find_all('a', href=True):
                href = a_tag['href']
                title = a_tag.get_text(strip=True)
                if href and title:
                    abs_url = urljoin(section_url, href)
                    if abs_url.startswith(BASE_URL):
                        events.add((abs_url, title))
    except Exception:
        pass
    return events

def extract_m3u8_links(page_url):
    links = set()
    try:
        resp = SESSION.get(page_url, timeout=10)
        resp.raise_for_status()
        links.update(M3U8_REGEX.findall(resp.text))
    except Exception:
        pass
    return links

def check_stream_status(m3u8_url):
    try:
        resp = SESSION.head(m3u8_url, timeout=5, allow_redirects=True)
        return resp.status_code == 200
    except Exception:
        return False

def main():
    # Header updated with x-tvg-url
    playlist_lines = [f'#EXTM3U x-tvg-url="{EPG_URL}"']
    sections = discover_sections(BASE_URL)
    
    for section_url, section_title in sections:
        event_links = discover_event_links(section_url)
        pages = event_links if event_links else {(section_url, section_title)}

        for event_url, event_title in pages:
            tv_id, logo = get_tv_info(event_url, event_title)
            m3u8_links = extract_m3u8_links(event_url)
            for link in m3u8_links:
                if check_stream_status(link):
                    playlist_lines.append(f'#EXTINF:-1 tvg-id="{tv_id}" tvg-logo="{logo}" group-title="Roxiestreams",{event_title}')
                    playlist_lines.append(link)

    with open("Roxiestreams.m3u", "w", encoding="utf-8") as f:
        f.write("\n".join(playlist_lines))
    logging.info("Playlist updated with EPG and Logos.")

if __name__ == "__main__":
    main()
