import os
import csv
import json
import random
import urllib.parse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('monitor_config')

# Load credentials from CSV
def load_credentials(csv_path='credentials.csv'):
    creds = {}
    try:
        if os.path.exists(csv_path):
            with open(csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    key = row.get('key', '').strip()
                    val = row.get('value', '').strip()
                    t = row.get('type', '').strip()
                    
                    if key:
                        creds[key] = val
                        creds[key.upper()] = val
                        creds[key.lower()] = val
                    if t:
                        creds[t] = val
                        creds[t.upper()] = val
                        creds[t.lower()] = val
                        if not val and key and key not in ('DISCORD_TOKEN', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'INSTAGRAM_USERNAME', 'INSTAGRAM_PASSWORD', 'INSTAGRAM_SESSIONID', 'OWNER_CHAT_ID', 'INSTAGRAM_CSRFTOKEN', 'INSTAGRAM_PROXY', 'INSTAGRAM_COOKIES'):
                            creds[t] = key
                            creds[t.upper()] = key
                            creds[t.lower()] = key
    except Exception as e:
        logger.error(f"Error loading credentials from CSV: {e}")
    return creds

credentials = load_credentials()

# Token and IDs
DISCORD_TOKEN = credentials.get('DISCORD_TOKEN', os.getenv('DISCORD_TOKEN') or "")
TELEGRAM_BOT_TOKEN = credentials.get('TELEGRAM_BOT_TOKEN', os.getenv('TELEGRAM_BOT_TOKEN') or "")
TELEGRAM_CHAT_ID = credentials.get('TELEGRAM_CHAT_ID', os.getenv('TELEGRAM_CHAT_ID') or "")
OWNER_CHAT_ID = credentials.get('OWNER_CHAT_ID', os.getenv('OWNER_CHAT_ID') or "")

# Instagram Settings
INSTAGRAM_USERNAME = credentials.get('INSTAGRAM_USERNAME', credentials.get('instagram_username', os.getenv('INSTAGRAM_USERNAME') or ''))
INSTAGRAM_PASSWORD = credentials.get('INSTAGRAM_PASSWORD', credentials.get('instagram_password', os.getenv('INSTAGRAM_PASSWORD') or ''))
INSTAGRAM_SESSIONID = credentials.get('INSTAGRAM_SESSIONID', credentials.get('instagram_sessionid', os.getenv('INSTAGRAM_SESSIONID') or ''))
INSTAGRAM_CSRFTOKEN = credentials.get('INSTAGRAM_CSRFTOKEN', credentials.get('instagram_csrftoken', os.getenv('INSTAGRAM_CSRFTOKEN') or ''))
INSTAGRAM_PROXY = credentials.get('INSTAGRAM_PROXY', credentials.get('instagram_proxy', os.getenv('INSTAGRAM_PROXY') or ''))
INSTAGRAM_COOKIES_RAW = credentials.get('INSTAGRAM_COOKIES', credentials.get('instagram_cookies', os.getenv('INSTAGRAM_COOKIES') or ''))

# Colors for Discord embeds
COLORS = {
    'primary': 0x3498db,      # Blue
    'success': 0x2ecc71,      # Green
    'warning': 0xf39c12,      # Orange
    'danger': 0xe74c3c,       # Red
    'purple': 0x9b59b6,       # Purple
    'dark': 0x2c3e50,         # Dark blue
    'light': 0xecf0f1,        # Light gray
    'gold': 0xf1c40f          # Gold
}

# User agents for requests
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
]

# Instagram App ID used in some public API headers
# Default to the common web/mobile app id to reduce 403/429 issues when missing
IG_APP_ID = '936619743392459'

# Monitoring defaults
# Conservative defaults to avoid Instagram rate-limits
MONITOR_INTERVAL_SECONDS = 900
# Seconds to sleep between individual account checks to avoid bursts
PER_ACCOUNT_SLEEP = 3.0
# Human-like behavior tuning
# Max concurrent outbound requests to Instagram
# Limit concurrency aggressively to appear human and avoid 429s
MAX_CONCURRENT_REQUESTS = 1
# Base delay (seconds) before requests to mimic human pacing
HUMAN_DELAY_BASE = 0.6
# Stddev/jitter for human delay
HUMAN_DELAY_JITTER = 0.5

# Disable Instaloader automatic fallback by default to avoid additional
# App-like requests that often trigger 429s. Set to True to re-enable.
USE_INSTALOADER = False

# Parse Cookies
INSTAGRAM_COOKIES = {}
if INSTAGRAM_COOKIES_RAW:
    try:
        parsed = json.loads(INSTAGRAM_COOKIES_RAW)
        if isinstance(parsed, dict):
            INSTAGRAM_COOKIES.update(parsed)
    except Exception:
        for item in INSTAGRAM_COOKIES_RAW.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                # URL-decode cookie values (sessionids may be percent-encoded)
                try:
                    v = urllib.parse.unquote(v)
                except Exception:
                    pass
                INSTAGRAM_COOKIES[k] = v

if INSTAGRAM_SESSIONID:
    try:
        INSTAGRAM_COOKIES['sessionid'] = urllib.parse.unquote(INSTAGRAM_SESSIONID)
    except Exception:
        INSTAGRAM_COOKIES['sessionid'] = INSTAGRAM_SESSIONID
if INSTAGRAM_CSRFTOKEN:
    INSTAGRAM_COOKIES['csrftoken'] = INSTAGRAM_CSRFTOKEN

# Load proxy list if proxies.txt exists
INSTAGRAM_PROXIES = []
if os.path.exists('proxies.txt'):
    try:
        with open('proxies.txt', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    INSTAGRAM_PROXIES.append(line)
    except Exception as pe:
        logger.warning(f"Error reading proxies.txt: {pe}")

# Fallback to single proxy
if INSTAGRAM_PROXY and not INSTAGRAM_PROXIES:
    INSTAGRAM_PROXIES.append(INSTAGRAM_PROXY)

def get_random_proxy():
    """Get a random proxy from the available proxy list and set it globally."""
    if INSTAGRAM_PROXIES:
        proxy = random.choice(INSTAGRAM_PROXIES)
        os.environ['HTTP_PROXY'] = proxy
        os.environ['HTTPS_PROXY'] = proxy
        os.environ['http_proxy'] = proxy
        os.environ['https_proxy'] = proxy
        return proxy
    return None

# Set default proxy if any loaded
default_proxy = get_random_proxy()
