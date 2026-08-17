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
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://www.google.com/'
}

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

def scrape_single_jav(video_url):
    try:
        res = session.get(video_url, headers=REQ_HEADERS, timeout=10)
        if res.status_code != 200:
            return

        soup = BeautifulSoup(res.text, 'html.parser')
        
        title_el = soup.find('h1') or soup.find('title')
        raw_title = title_el.text.strip() if title_el else ''
        title = clean_title(raw_title)
        
        if not title:
            return

        servers = []
        for i in soup.find_all(['iframe', 'embed']):
            src = i.get('src') or i.get('data-src') or i.get('data-lazy-src') or ''
            if src and not any(bad in src for bad in ['facebook.com', 'ads', 'twitter.com', 'google.com']):
                if src not in servers:
                    servers.append(src)

        if not servers or is_video_exists(servers[0]):
            return

        thumbnail = ''
        thumb_el = soup.find('meta', property='og:image')
        if thumb_el:
            thumbnail = thumb_el.get('content', '')

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
            'hashtags': ['JAV', 'Uncensored'],
            'created_at': datetime.now(timezone.utc).isoformat()
        }

        save_res = session.post(f"{SUPABASE_URL}/videos", headers=HEADERS, json=payload, timeout=10)
        if save_res.status_code in [200, 201]:
            print(f"⚡ Saved: {title[:30]}...")

    except Exception as e:
        print(f"Error scraping {video_url}: {e}")

def scrape_page(page_num, base_url):
    page_url = f"{base_url}/page/{page_num}/" if page_num > 1 else base_url + "/"
    print(f"\n🚀 --- Scraping Page {page_num}: {page_url} ---")

    try:
        res = session.get(page_url, headers=REQ_HEADERS, timeout=10)
        if res.status_code != 200:
            print(f"Failed to fetch page {page_num}, Status: {res.status_code}")
            return

        soup = BeautifulSoup(res.text, 'html.parser')
        links = set()

        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(base_url, href)
            if base_url in full_url and full_url != base_url and full_url != base_url + '/':
                bad_keywords = ['/page/', '/category/', '/tag/', '#', '/contact', '/dmca', '/about']
                if not any(ign in full_url for ign in bad_keywords):
                    links.add(full_url)

        print(f"🎯 Found {len(links)} links on Page {page_num}. Processing...")

        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(scrape_single_jav, links)

    except Exception as e:
        print(f"Page Fetch Error: {e}")

def run_jav_scraper():
    base_url = "https://www.javxxxporn.com"
    
    # ၁။ Video အသစ်များအတွက် Page 1 မှ 3 ထိ စစ်ဆေးခြင်း
    print("✨ Checking latest pages for new videos...")
    for page in range(1, 4):
        scrape_page(page, base_url)

    # ၂။ Page 611 ကနေ 1 ထိ ဗျောင်းပြန်လှည့်၍ စစ်ဆေးခြင်း (အဟောင်းများဆွဲရန်)
    # GitHub Actions မှာ Timeout မဖြစ်အောင် တစ်ကြိမ် Run လျှင် Page 10 မျက်နှာခန့် လုပ်ဆောင်နိုင်ပါသည်
    START_PAGE = 611
    END_PAGE = 1
    
    print(f"\n🔄 Reverse Scraping from Page {START_PAGE} down to {END_PAGE}...")
    for page in range(START_PAGE, END_PAGE - 1, -1):
        scrape_page(page, base_url)

if __name__ == '__main__':
    run_jav_scraper()
        
