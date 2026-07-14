import asyncio
import random
import logging
from datetime import datetime
import instaloader
from instaloader.exceptions import LoginRequiredException, BadCredentialsException, ConnectionException, ProfileNotExistsException
import requests
import time
import os
import urllib.parse
from session_manager import get_session
import database
import notifier
import config

logger = logging.getLogger('monitor_service')

# Concurrency control to limit simultaneous requests and mimic human behavior
REQUEST_SEMAPHORE = asyncio.Semaphore(getattr(config, 'MAX_CONCURRENT_REQUESTS', 3))

async def human_delay():
    """Sleep a short randomized interval to mimic human pacing."""
    try:
        base = float(getattr(config, 'HUMAN_DELAY_BASE', 0.6))
        jitter = float(getattr(config, 'HUMAN_DELAY_JITTER', 0.5))
        delay = max(0.05, random.gauss(base, jitter))
        await asyncio.sleep(delay)
    except Exception:
        await asyncio.sleep(0.5)

# --- HTTP request helper (with retries/backoff and proxy rotation) ---
async def _retry_request(method, url, session, max_retries=3, backoff_factor=0.5, **kwargs):
    """Perform an HTTP request with retry/backoff and optional proxy rotation.

    Keeps the same calling convention (method, url, session, **kwargs) so callers
    can continue to use `async with resp as r:` semantics.
    """
    attempt = 0
    last_resp = None
    last_exc = None
    while attempt <= max_retries:
        attempt += 1
        # pick a proxy per-attempt to rotate on failures
        proxy = config.get_random_proxy()
        if proxy:
            kwargs['proxy'] = proxy
        try:
            resp = await method(url, **kwargs)
            last_resp = resp
            # Inspect status without consuming body by using context in caller
            status = getattr(resp, 'status', None)
            if status == 429 or (status is not None and 500 <= status < 600):
                # backoff and retry
                sleep_for = backoff_factor * (2 ** (attempt - 1))
                await asyncio.sleep(sleep_for)
                continue
            return resp
        except Exception as e:
            last_exc = e
            sleep_for = backoff_factor * (2 ** (attempt - 1))
            await asyncio.sleep(sleep_for)
            continue

    # Exhausted retries: if we have a last response, return it; otherwise raise
    if last_resp:
        return last_resp
    if last_exc:
        raise last_exc
    # Fallback: raise generic error
    raise RuntimeError('Request failed after retries')

async def fetch_instagram_data_web_api(username):
    try:
        session = await get_session()
        username = username.lstrip('@')
        url = f"https://www.instagram.com/{username}/?__a=1&__d=dis"
        headers = {
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'referer': f'https://www.instagram.com/{username}/',
            'user-agent': random.choice(config.USER_AGENTS),
            'x-ig-app-id': config.IG_APP_ID
        }
        if config.INSTAGRAM_CSRFTOKEN:
            headers['x-csrftoken'] = config.INSTAGRAM_CSRFTOKEN
        # Add Cookie header if cookies configured
        if config.INSTAGRAM_COOKIES:
            try:
                cookie_header = '; '.join([f"{k}={v}" for k, v in config.INSTAGRAM_COOKIES.items()])
                headers['cookie'] = cookie_header
            except Exception:
                pass
            
        kwargs = {'headers': headers, 'timeout': 15, 'allow_redirects': False}
        proxy = config.get_random_proxy()
        if proxy:
            kwargs['proxy'] = proxy

        async with REQUEST_SEMAPHORE:
            await human_delay()
            resp = await _retry_request(session.get, url, session, **kwargs)
            async with resp as r:
                if r.status == 200:
                    data = await r.json()
                    user = None
                    if isinstance(data, dict):
                        if 'graphql' in data and 'user' in data['graphql']:
                            user = data['graphql']['user']
                        elif 'data' in data and 'user' in data['data']:
                            user = data['data']['user']

                    if not user:
                        return {'success': False, 'status_code': r.status, 'error': 'User data not found in response'}

                    return {
                        'success': True,
                        'username': username,
                        'full_name': user.get('full_name') or user.get('username', username),
                        'biography': user.get('biography', '') or '',
                        'followers': (user.get('edge_followed_by') or {}).get('count', user.get('follower_count', 0)) if isinstance(user.get('edge_followed_by', {}), dict) else user.get('follower_count', 0),
                        'following': (user.get('edge_follow') or {}).get('count', user.get('following_count', 0)) if isinstance(user.get('edge_follow', {}), dict) else user.get('following_count', 0),
                        'posts': (user.get('edge_owner_to_timeline_media') or {}).get('count', user.get('media_count', 0)) if isinstance(user.get('edge_owner_to_timeline_media', {}), dict) else user.get('media_count', 0),
                        'profile_pic_url': user.get('profile_pic_url_hd') or user.get('profile_pic_url') or None,
                        'is_private': user.get('is_private', False),
                        'is_verified': user.get('is_verified', False),
                        'external_url': user.get('external_url', None)
                    }
                elif r.status == 302:
                    # Redirecting means the page is active but wants login page
                    return {'success': False, 'status_code': r.status, 'error': 'Redirected to login page (active but restricted)'}
                elif r.status == 429:
                    return {'success': False, 'status_code': r.status, 'error': 'rate_limited'}
                else:
                    return {'success': False, 'status_code': r.status, 'error': f'HTTP status {r.status}'}
    except Exception as e:
        logger.warning(f"Web API exception for {username}: {e}")
        return {'success': False, 'error': f'Web API error: {e}'}

async def fetch_instagram_data_mobile_api(username):
    try:
        session = await get_session()
        username = username.lstrip('@')
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        
        headers = {
            'User-Agent': 'Instagram 6.12.1 Android (30/11; 480dpi; 1080x2004; HONOR; ANY-LX2; HNANY-Q1; qcom; ar_EG_#u-nu-arab)',
            'Accept-Language': 'ar-EG, en-US',
            'X-IG-Connection-Type': 'MOBILE(LTE)',
            'X-IG-Capabilities': 'AQ==',
            'Accept': '*/*',
            'X-IG-App-ID': config.IG_APP_ID
        }
        if config.INSTAGRAM_CSRFTOKEN:
            headers['x-csrftoken'] = config.INSTAGRAM_CSRFTOKEN
        # Attach cookies as header when available to reduce rate-limiting
        if config.INSTAGRAM_COOKIES:
            try:
                cookie_header = '; '.join([f"{k}={v}" for k, v in config.INSTAGRAM_COOKIES.items()])
                headers['cookie'] = cookie_header
            except Exception:
                pass
            
        kwargs = {'headers': headers}
        proxy = config.get_random_proxy()
        if proxy:
            kwargs['proxy'] = proxy
        
        async with REQUEST_SEMAPHORE:
            await human_delay()
            resp = await _retry_request(session.get, url, session, **kwargs)
            async with resp as response:
                if response.status == 200:
                    data = await response.json()
                    if 'user' in data:
                        user = data['user']
                        return {
                            'success': True,
                            'username': username,
                            'full_name': user.get('full_name', 'Not available'),
                            'biography': user.get('biography', 'No bio'),
                            'followers': user.get('follower_count', 0),
                            'following': user.get('following_count', 0),
                            'posts': user.get('media_count', 0),
                            'profile_pic_url': user.get('profile_pic_url', None),
                            'is_private': user.get('is_private', False),
                            'is_verified': user.get('is_verified', False),
                            'external_url': user.get('external_url', None)
                        }
                    else:
                        return {'success': False, 'status_code': response.status, 'error': 'User not found in mobile API response'}
                elif response.status == 429:
                    return {'success': False, 'status_code': response.status, 'error': 'rate_limited'}
                else:
                    return {'success': False, 'status_code': response.status, 'error': f'Mobile API HTTP {response.status}'}
    except Exception as e:
        logger.error(f"Mobile API error for {username}: {str(e)}")
        return {'success': False, 'error': f'Mobile API error: {str(e)}'}

async def fetch_instagram_data_instaloader(username):
    try:
        username = username.lstrip('@')

        def sync_fetch(usern):
            L = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                compress_json=False,
                max_connection_attempts=3,
                request_timeout=30
            )
            
            proxy = config.get_random_proxy()
            if proxy:
                # Instaloader uses requests internally; set proxy mapping
                try:
                    L.context._session.proxies = {'http': proxy, 'https': proxy}
                except Exception:
                    pass

            # Populate cookies into Instaloader session
            if config.INSTAGRAM_COOKIES:
                try:
                    L.context._session.cookies.update(config.INSTAGRAM_COOKIES)
                except Exception:
                    pass

            # Ensure headers include UA and csrf token to mimic browser
            try:
                ua = random.choice(config.USER_AGENTS)
                L.context._session.headers.update({'User-Agent': ua, 'Referer': f'https://www.instagram.com/{usern}/'})
                if config.INSTAGRAM_CSRFTOKEN:
                    L.context._session.headers.update({'x-csrftoken': config.INSTAGRAM_CSRFTOKEN})
            except Exception:
                pass

            # If no session cookie present, attempt login as fallback
            if not config.INSTAGRAM_COOKIES or 'sessionid' not in config.INSTAGRAM_COOKIES:
                try:
                    if config.INSTAGRAM_USERNAME and config.INSTAGRAM_PASSWORD:
                        L.login(config.INSTAGRAM_USERNAME, config.INSTAGRAM_PASSWORD)
                except Exception as le:
                    logger.warning(f"Instaloader login fallback failed: {le}")

            profile = instaloader.Profile.from_username(L.context, usern)
            return {
                'username': profile.username,
                'full_name': profile.full_name or 'Not available',
                'biography': profile.biography or 'No bio',
                'followers': profile.followers,
                'following': profile.followees,
                'posts': profile.mediacount,
                'profile_pic_url': profile.profile_pic_url,
                'is_private': profile.is_private,
                'is_verified': profile.is_verified,
                'external_url': profile.external_url
            }

        # Limit concurrency and add human-like delay before heavy Instaloader work
        async with REQUEST_SEMAPHORE:
            await human_delay()
            result = await asyncio.to_thread(sync_fetch, username)
            return {'success': True, **result}
    except ProfileNotExistsException as e:
        return {'success': False, 'status_code': 404, 'error': 'ProfileNotExistsException (Banned or Deleted)'}
    except LoginRequiredException:
        return {'success': False, 'status_code': 401, 'error': 'Login required'}
    except BadCredentialsException:
        return {'success': False, 'status_code': 401, 'error': 'Invalid credentials'}
    except ConnectionException as e:
        return {'success': False, 'error': f'Connection error: {str(e)}'}
    except Exception as e:
        logger.error(f"Instaloader error for {username}: {str(e)}")
        return {'success': False, 'error': f'Instaloader error: {str(e)}'}

async def get_instagram_data(username):
    """Get Instagram data using multiple methods with fallback"""
    methods = [
        ("Web API", fetch_instagram_data_web_api),
        ("Mobile API", fetch_instagram_data_mobile_api),
    ]
    # Optionally include Instaloader as a last-resort fallback
    if getattr(config, 'USE_INSTALOADER', False):
        methods.append(("Instaloader", fetch_instagram_data_instaloader))
    
    last_error = None
    for method_name, method_func in methods:
        try:
            logger.info(f"Trying {method_name} for {username}")
            result = await method_func(username)
            if result['success']:
                logger.info(f"Successfully fetched data using {method_name}")
                return result
            else:
                last_error = result
                logger.warning(f"{method_name} failed: {result.get('error')}")
        except Exception as e:
            logger.error(f"{method_name} exception: {str(e)}")
            continue
            
    return last_error or {'success': False, 'error': 'All scraping methods failed'}

async def check_account_status(username):
    result = await get_instagram_data(username)
    if result.get('success'):
        return 'active', result

    error_msg = result.get('error', '').lower()
    status_code = result.get('status_code', None)

    if status_code == 429 or 'rate_limited' in error_msg:
        return 'rate_limited', result

    if status_code == 404 or 'profilenotexistsexception' in error_msg or 'not found' in error_msg:
        return 'banned', result
    else:
        # Check redirects or auth issues
        if status_code == 302 or 'login page' in error_msg:
            # Active but restricted by login screen redirect
            return 'active', result
        return 'error', result

async def run_monitoring_cycle(bot):
    accounts = database.get_monitored_accounts()
    # Shuffle order to avoid predictable access patterns
    try:
        random.shuffle(accounts)
    except Exception:
        pass

    if not accounts:
        logger.info("No accounts to monitor.")
        return
        
    logger.info(f"Starting monitoring cycle for {len(accounts)} accounts...")
    for acc in accounts:
        username = acc['username']
        old_status = acc['status']
        channel_id = acc['channel_id']
        
        status, data = await check_account_status(username)
        
        if status == 'active':
            database.update_account_state(
                username, 
                status='active', 
                followers=data.get('followers', 0),
                following=data.get('following', 0),
                posts=data.get('posts', 0),
                full_name=data.get('full_name'),
                is_private=data.get('is_private', 0),
                is_verified=data.get('is_verified', 0)
            )
            
            if old_status == 'banned':
                msg = f"🎉 **Account Unbanned / Recovered!**\n👤 **Username:** @{username}\n📊 **Followers:** {data.get('followers', 0):,}"
                await notifier.send_discord_notification(channel_id, content=msg)
                
                telegram_msg = f"🎉 <b>Account Unbanned / Recovered!</b>\n👤 <b>Username:</b> @{username}\n📊 <b>Followers:</b> {data.get('followers', 0):,}"
                notifier.send_telegram_notification(telegram_msg)
                database.log_event(username, 'status_change', "Account state changed: banned -> active")
            elif old_status == 'unknown':
                database.log_event(username, 'info', "Initialized account state: active")
                
        elif status == 'banned':
            database.update_account_state(
                username, 
                status='banned',
                followers=acc['followers'],
                following=acc['following'],
                posts=acc['posts'],
                full_name=acc['full_name'],
                is_private=acc['is_private'],
                is_verified=acc['is_verified']
            )
            
            if old_status == 'active':
                msg = f"🚨 **Account Banned / Deleted!**\n👤 **Username:** @{username}\n📊 **Last Known Followers:** {acc.get('followers', 0):,}"
                await notifier.send_discord_notification(channel_id, content=msg)
                
                telegram_msg = f"🚨 <b>Account Banned / Deleted!</b>\n👤 <b>Username:</b> @{username}\n📊 <b>Last Known Followers:</b> {acc.get('followers', 0):,}"
                notifier.send_telegram_notification(telegram_msg)
                database.log_event(username, 'status_change', "Account state changed: active -> banned")
            elif old_status == 'unknown':
                database.log_event(username, 'info', "Initialized account state: banned")
                
        elif status == 'rate_limited':
            logger.warning(f"Rate limit detected for {username}. Skipping update.")
            database.log_event(username, 'check_failed', "Rate limit hit during monitor cycle")
        else:
            logger.warning(f"Check failed for {username}: {data.get('error')}")
            database.log_event(username, 'check_failed', f"Error checking: {data.get('error')}")
        
        # Sleep between account checks to avoid bursting requests
        try:
            await asyncio.sleep(config.PER_ACCOUNT_SLEEP)
        except Exception:
            # ignore sleep interruptions
            pass

async def start_monitoring_loop(bot, interval_seconds=None):
    """Periodically execute the monitoring cycle."""
    if interval_seconds is None:
        interval_seconds = config.MONITOR_INTERVAL_SECONDS
    logger.info(f"Background monitoring loop started (Interval: {interval_seconds}s).")
    while True:
        try:
            await run_monitoring_cycle(bot)
        except Exception as e:
            logger.error(f"Error in monitoring loop cycle: {e}")
        # Sleep for configured interval
        await asyncio.sleep(interval_seconds)
