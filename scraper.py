import requests
import re
import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from urllib.parse import urljoin
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

SUPABASE_URL = 'https://esxxyoguiwkhivydfnzg.supabase.co/rest/v1'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVzeHh5b2d1aXdraGl2eWRmbnpnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODU5NDI0ODksImV4cCI6MjEwMTUxODQ4OX0.J-zgz71xmLEZ6Kb0-K2--27yMd9Wfs75XcA392cnOWo'

HEADERS = {
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {SUPABASE_KEY}',
    'Content-Type': 'application/json',
    'Prefer': 'return=minimal'
}

REQ_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://google.com'
}

VALID_STREAM_DOMAINS = [
    'streamtape', 'dood', 'vidoza', 'mixdrop', 'filelions', 
    'streamwish', 'swisha', 'voe.sx', 'lulustream', 'streamhide', 
    'abysscdn', 'vidhide', 'm2df', 'embed', 'player', 'hls'
]

session = requests.Session()

def is_video_exists(video_url):
    if not video_url:
        return False
    try:
        res = session.get(f"{SUPABASE_URL}/videos?video_url=eq.{video_url}", headers=HEADERS, timeout=5)
        if res.status_code == 200 and len(res.json()) > 0:
            return True
    except Exception:
        pass
    return False

def clean_title(title):
    if not title:
        return ""
    title = re.sub(r'\*+[a-zA-Z0-9_*]+\*+', '', title)
    return title.strip()

def is_valid_jav(title, page_text):
    title_upper = title.upper()
    if re.search(r'[A-Z0-9]{2,8}[-_][0-9]{3,5}', title_upper):
        return True
    if any(kw in title_upper for kw in ['JAV', 'JAPANESE', 'UNCENSORED', 'CENSORED', 'SUBTITLE']):
        return True
    if re.search(r'[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]', page_text):
        return True
    return False

def scrape_single_jav(video_url):
    try:
        res = session.get(video_url, headers=REQ_HEADERS, timeout=10)
        if res.status_code != 200:
            return

        soup = BeautifulSoup(res.text, 'html.parser')
        title_el = soup.find('h1', class_=lambda c: c and 'entry-title' in c) or soup.find('h1')
        raw_title = title_el.text.strip() if title_el else ''
        if not raw_title and soup.title:
            raw_title = soup.title.text.split('-')[0].split('|')[0].strip()

        title = clean_title(raw_title)
        if not title or title.lower() in ['home', 'jav'] or not is_valid_jav(title, res.text):
            return

        servers = []
        for i in soup.find_all(['iframe', 'embed']):
            src = i.get('src') or i.get('data-src') or i.get('data-lazy-src') or ''
            if src and not any(bad in src for bad in ['facebook.com', 'ads', 'twitter.com', 'google.com']):
                if any(domain in src.lower() for domain in VALID_STREAM_DOMAINS) or 'embed' in src.lower():
                    if src not in servers:
                        servers.append(src)

        if not servers or is_video_exists(servers[0]):
            return

        thumbnail = ''
        thumb_el = soup.find('meta', property='og:image')
        if thumb_el:
            thumbnail = thumb_el.get('content', '')

        hashtags = ['JAV']
        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords and meta_keywords.get('content'):
            for tag in meta_keywords['content'].split(','):
                clean_tag = tag.strip().title().replace(' ', '')
                if clean_tag and clean_tag not in hashtags:
                    hashtags.append(clean_tag)

        payload = {
            'title': title,
            'thumbnail': thumbnail,
            'video_url': servers[0],
            'server1_url': servers[0],
            'server2_url': servers[1] if len(servers) > 1 else '',
            'server3_url': servers[2] if len(servers) > 2 else '',
            'video_type': 'embed',
            'country': 'JAV',
            'channel': 'JAV Collection',
            'hashtags': hashtags[:10],
            'created_at': datetime.now(timezone.utc).isoformat()
        }

        save_res = session.post(f"{SUPABASE_URL}/videos", headers=HEADERS, json=payload, timeout=10)
        if save_res.status_code in [200, 201]:
            print(f"⚡ Saved [JAV]: {title[:25]}...")

    except Exception as e:
        print(f"Error: {e}")

def run_jav_scraper():
    # GitHub Action တွင် Auto Run စေရန် Website URL ပြင်ဆင်နိုင်ပါသည်
    base_url = "https://javmost.cx" 
    
    for current_page in range(1, 3):
        page_url = f"{base_url}/page/{current_page}/" if current_page > 1 else base_url + "/"
        print(f"\n🚀 --- Scraping Page {current_page} ---")

        try:
            res = session.get(page_url, headers=REQ_HEADERS, timeout=10)
            if res.status_code != 200:
                continue

            soup = BeautifulSoup(res.text, 'html.parser')
            links = set()

            for a in soup.find_all('a', href=True):
                href = a['href']
                full_url = urljoin(base_url, href)
                if base_url in full_url:
                    bad_keywords = ['/page/', '/category/', '/tag/', '#', '/contact', '/dmca', '/about']
                    if not any(ign in full_url for ign in bad_keywords):
                        if full_url != base_url and full_url != base_url + '/':
                            links.add(full_url)

            print(f"🎯 Found {len(links)} links. Processing...")

            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(scrape_single_jav, links)

        except Exception as e:
            print(f"Error: {e}")

if __name__ == '__main__':
    run_jav_scraper()

