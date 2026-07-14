import asyncio
import os
import sys
# Ensure project root is on sys.path so local modules can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from session_manager import get_session
import config

async def main():
    session = await get_session()
    username = config.INSTAGRAM_USERNAME or 'instagram'
    url = f'https://i.instagram.com/api/v1/users/web_profile_info/?username={username}'
    headers = {
        'User-Agent': 'Instagram 6.12.1 Android (30/11; 480dpi; 1080x2004; HONOR; ANY-LX2; HNANY-Q1; qcom; ar_EG_#u-nu-arab)',
        'X-IG-App-ID': config.IG_APP_ID,
        'Accept': '*/*'
    }
    if config.INSTAGRAM_CSRFTOKEN:
        headers['x-csrftoken'] = config.INSTAGRAM_CSRFTOKEN
    try:
        async with session.get(url, headers=headers, timeout=15) as r:
            print('STATUS:', r.status)
            print('HEADERS:', dict(r.headers))
            text = await r.text()
            print('BODY_SNIPPET:', text[:2000])
    except Exception as e:
        print('ERROR:', e)

if __name__ == '__main__':
    asyncio.run(main())
