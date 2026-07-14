import instaloader
import os
import sys
# Ensure project root is on sys.path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import config
import csv
import os
import urllib.parse

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.csv')

def write_credential(key, value):
    # Read CSV
    rows = []
    found = False
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('key') and row.get('key').lower() == key.lower():
                row['value'] = value
                found = True
            rows.append(row)
    if not found:
        rows.append({'type': key, 'key': key, 'value': value})
    # Write back
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['type','key','value']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main():
    username = config.INSTAGRAM_USERNAME
    password = config.INSTAGRAM_PASSWORD
    if not username or not password:
        print('Username or password missing in config. Aborting.')
        return

    L = instaloader.Instaloader(dirname_pattern='.', download_pictures=False, download_comments=False, save_metadata=False)
    # Configure session headers, cookies, and proxy from config
    try:
        ua = config.USER_AGENTS[0] if config.USER_AGENTS else 'Mozilla/5.0'
        try:
            L.context._session.headers.update({'User-Agent': ua, 'Referer': f'https://www.instagram.com/'})
        except Exception:
            pass
        if config.INSTAGRAM_COOKIES:
            try:
                L.context._session.cookies.update(config.INSTAGRAM_COOKIES)
            except Exception:
                pass
        proxy = config.get_random_proxy()
        if proxy:
            try:
                L.context._session.proxies = {'http': proxy, 'https': proxy}
            except Exception:
                pass

        L.login(username, password)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('Login failed:', repr(e))
        return

    # Extract cookies
    cookies = {}
    try:
        for cookie in L.context._session.cookies:
            cookies[cookie.name] = cookie.value
    except Exception as e:
        print('Failed to read cookies from Instaloader session:', e)
        return

    sessionid = cookies.get('sessionid')
    csrftoken = cookies.get('csrftoken')
    print('Obtained cookies:', {k: (v[:6] + '...' if len(v)>6 else v) for k,v in cookies.items()})

    # Persist sessionid and csrftoken and full cookies
    if sessionid:
        write_credential('instagram_sessionid', sessionid)
        print('Wrote instagram_sessionid to credentials.csv')
    if csrftoken:
        write_credential('instagram_csrftoken', csrftoken)
        print('Wrote instagram_csrftoken to credentials.csv')

    # Also write full cookies string
    cookie_str = '; '.join([f"{k}={urllib.parse.quote(v)}" for k,v in cookies.items()])
    write_credential('instagram_cookies', cookie_str)
    print('Wrote instagram_cookies to credentials.csv')

if __name__ == '__main__':
    main()
