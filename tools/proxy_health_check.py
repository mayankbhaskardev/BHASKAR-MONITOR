import asyncio
import aiohttp
import time
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PROXIES_FILE = ROOT / 'proxies.txt'

# Lightweight check URL — httpbin is good for checking proxy behavior
TEST_URL = 'https://httpbin.org/get'

# Concurrency limit
CONCURRENCY = 5
TIMEOUT = 12

async def check_single(session, proxy, sem):
    async with sem:
        start = time.perf_counter()
        try:
            async with session.get(TEST_URL, proxy=proxy, timeout=TIMEOUT) as resp:
                elapsed = time.perf_counter() - start
                status = resp.status
                headers = dict(resp.headers)
                text = await resp.text()
                # Reject common blocking statuses
                if status >= 400:
                    return proxy, False, status, elapsed, headers
                # Some proxy providers or Instagram blocking may return empty body
                if not text:
                    return proxy, False, status, elapsed, headers
                # Also check for Proxy-Status header that indicates blocking
                proxy_status = headers.get('Proxy-Status') or headers.get('Proxy-Status-Code')
                if proxy_status and ('blocked' in proxy_status.lower() or 'invalid' in proxy_status.lower()):
                    return proxy, False, status, elapsed, headers
                return proxy, True, status, elapsed, headers
        except Exception as e:
            elapsed = time.perf_counter() - start
            return proxy, False, str(e), elapsed, {}

async def main():
    if not PROXIES_FILE.exists():
        print(f"No proxies file found at {PROXIES_FILE}")
        return 1
    proxies = [line.strip() for line in PROXIES_FILE.read_text(encoding='utf-8').splitlines() if line.strip() and not line.strip().startswith('#')]
    if not proxies:
        print("No proxies to check.")
        return 0

    sem = asyncio.Semaphore(CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=TIMEOUT)
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        tasks = [check_single(session, p, sem) for p in proxies]
        results = await asyncio.gather(*tasks)

    healthy = []
    bad = []
    for proxy, ok, status, elapsed, headers in results:
        if ok:
            healthy.append((proxy, status, elapsed))
        else:
            bad.append((proxy, status, elapsed))

    # Overwrite proxies.txt with healthy proxies
    if healthy:
        PROXIES_FILE.write_text('\n'.join([p for p, s, e in healthy]) + '\n', encoding='utf-8')
    else:
        # No healthy proxies — keep original file but comment out bad ones
        PROXIES_FILE.write_text('\n'.join([f"# {p}  # BAD: {s}" for p, s, e in bad]) + '\n', encoding='utf-8')

    print('Proxy check complete')
    print(f'Healthy: {len(healthy)} | Bad: {len(bad)}')
    if healthy:
        print('\nHealthy proxies:')
        for p, s, e in healthy:
            print(f'- {p} (status={s}, {e:.2f}s)')
    if bad:
        print('\nBad proxies:')
        for p, s, e in bad:
            print(f'- {p} (reason={s}, {e:.2f}s)')

    return 0

if __name__ == '__main__':
    code = asyncio.run(main())
    sys.exit(code)
