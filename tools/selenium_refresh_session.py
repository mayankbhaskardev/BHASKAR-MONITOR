import os
import sys
import time
import csv
import urllib.parse

# Ensure project root is importable
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CSV_PATH = os.path.join(ROOT, 'credentials.csv')


def write_credential(key, value):
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
        print('Instagram username/password not set in config. Aborting.')
        return

    options = webdriver.ChromeOptions()
    # Use headless if display not available; Chrome may detect headless—try headless with flags
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--lang=en-US')
    options.add_argument('start-maximized')
    # Run in headful mode so interactive login can complete
    # (do not enable headless)

    # Set user-agent from config
    try:
        ua = config.USER_AGENTS[0]
        options.add_argument(f'--user-agent={ua}')
    except Exception:
        pass

    service = Service(ChromeDriverManager().install())
    # Temporarily unset proxy env vars to avoid chromedriver attempting to use them for localhost
    proxy_env_keys = ['HTTP_PROXY', 'http_proxy', 'HTTPS_PROXY', 'https_proxy']
    saved_proxy = {k: os.environ.pop(k, None) for k in proxy_env_keys}
    try:
        driver = webdriver.Chrome(service=service, options=options)
    finally:
        # restore proxy envs so subsequent requests can use them
        for k, v in saved_proxy.items():
            if v is not None:
                os.environ[k] = v
    try:
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        wait = WebDriverWait(driver, 30)
        driver.get('https://www.instagram.com/accounts/login/')

        # Wait for username field
        # Open login page and let the user log in manually in the visible browser
        print('Browser opened. Please log into Instagram manually in the opened window.')
        print('After you finish logging in, return to this terminal and press Enter to continue.')
        input('Press Enter after logging in...')
        # short delay to ensure cookies are set
        time.sleep(2)

        cookies = driver.get_cookies()
        cookie_dict = {c['name']: c['value'] for c in cookies}
        print('Retrieved cookies keys:', list(cookie_dict.keys()))

        sessionid = cookie_dict.get('sessionid')
        csrftoken = cookie_dict.get('csrftoken')

        if sessionid:
            write_credential('instagram_sessionid', sessionid)
            print('Wrote instagram_sessionid')
        if csrftoken:
            write_credential('instagram_csrftoken', csrftoken)
            print('Wrote instagram_csrftoken')

        # Persist full cookies as URL-encoded string
        cookie_str = '; '.join([f"{k}={urllib.parse.quote(v)}" for k, v in cookie_dict.items()])
        write_credential('instagram_cookies', cookie_str)
        print('Wrote instagram_cookies')

    except Exception as e:
        import traceback
        traceback.print_exc()
        print('Selenium login error:', e)
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    main()
