import aiohttp
import logging
from config import INSTAGRAM_COOKIES

logger = logging.getLogger('session_manager')

session = None

async def get_session():
    """Get or create a shared aiohttp ClientSession."""
    global session
    if session is None or session.closed:
        try:
            session = aiohttp.ClientSession(cookies=INSTAGRAM_COOKIES or None)
            logger.info("Created aiohttp ClientSession with configured cookies.")
        except Exception as e:
            logger.error(f"Error creating ClientSession with cookies: {e}. Falling back to clean session.")
            session = aiohttp.ClientSession()
    return session

async def close_session():
    """Close the shared ClientSession."""
    global session
    if session and not session.closed:
        await session.close()
        logger.info("Closed the shared ClientSession.")
