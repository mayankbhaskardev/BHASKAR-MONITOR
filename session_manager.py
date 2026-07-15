import asyncio
import logging
import aiohttp

from config import INSTAGRAM_COOKIES

logger = logging.getLogger("session_manager")

# Shared session instance
_session: aiohttp.ClientSession | None = None

# Prevent race conditions when creating/closing the session
_session_lock = asyncio.Lock()


async def get_session() -> aiohttp.ClientSession:
    """
    Returns a shared aiohttp ClientSession.
    Creates a new session if one does not already exist or has been closed.
    """

    global _session

    async with _session_lock:
        if _session is None or _session.closed:
            try:
                _session = aiohttp.ClientSession(
                    cookies=INSTAGRAM_COOKIES or None,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/138.0.0.0 Safari/537.36"
                        )
                    },
                )
                logger.info("Created shared ClientSession with configured cookies.")
            except Exception:
                logger.exception(
                    "Failed to create ClientSession with cookies. "
                    "Falling back to clean session."
                )
                _session = aiohttp.ClientSession()

        return _session


async def close_session() -> None:
    """
    Closes the shared ClientSession safely.
    """

    global _session

    async with _session_lock:
        if _session is not None and not _session.closed:
            await _session.close()
            logger.info("Closed shared ClientSession.")

        _session = None


async def recreate_session() -> aiohttp.ClientSession:
    """
    Forces creation of a fresh session.
    """

    await close_session()
    return await get_session()


def session_exists() -> bool:
    """
    Returns True if a usable session currently exists.
    """

    return _session is not None and not _session.closed