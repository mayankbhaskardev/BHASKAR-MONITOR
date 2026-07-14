import requests
import logging
import hashlib
import time
import discord
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger('notifier')

# Bot reference stored here dynamically to avoid circular imports
discord_bot = None

# Lightweight dedupe cache to avoid spamming identical Telegram messages
_TELEGRAM_RECENT = {}
_TELEGRAM_PRUNE_INTERVAL = 60 * 60  # 1 hour

def init_notifier(bot):
    global discord_bot
    discord_bot = bot
    logger.info("Notifier initialized with Discord bot instance.")

async def send_discord_notification(channel_id, content=None, embed=None):
    if not discord_bot:
        logger.warning("Discord bot reference not set in notifier.")
        return False
    if not channel_id:
        logger.warning("No channel_id provided for Discord notification.")
        return False
    try:
        channel = discord_bot.get_channel(int(channel_id))
        if not channel:
            channel = await discord_bot.fetch_channel(int(channel_id))
        if channel:
            if embed:
                await channel.send(content=content, embed=embed)
            else:
                await channel.send(content=content)
            logger.info(f"Discord notification sent to channel {channel_id}")
            return True
        else:
            logger.warning(f"Could not find Discord channel with ID {channel_id}")
            return False
    except Exception as e:
        logger.error(f"Error sending Discord notification: {e}")
        return False

def send_telegram_notification(message, parse_mode='HTML', dedupe_seconds: int = 10):
    """Send a notification to Telegram bot/channel with duplicate suppression."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing - skipping notification")
        return False

    try:
        now_ts = time.time()
        # Prune old entries
        to_delete = [k for k, v in _TELEGRAM_RECENT.items() if now_ts - v > _TELEGRAM_PRUNE_INTERVAL]
        for k in to_delete:
            del _TELEGRAM_RECENT[k]

        key = hashlib.sha256(message.encode('utf-8')).hexdigest()
        last = _TELEGRAM_RECENT.get(key)
        if last and (now_ts - last) < dedupe_seconds:
            logger.info("Skipping duplicate Telegram message (dedupe)")
            return False

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }

        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code == 200:
            _TELEGRAM_RECENT[key] = now_ts
            logger.info("Telegram notification sent successfully")
            return True
        else:
            logger.warning(f"Telegram send failed: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Exception while sending Telegram notification: {e}")
        return False

def send_telegram_photo(fileobj, caption: str = None, filename: str = 'photo.jpg', parse_mode: str = 'HTML'):
    """Send a photo (file-like object) to Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials missing - skipping photo send")
        return False

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        files = {'photo': (filename, fileobj)}
        data = {'chat_id': TELEGRAM_CHAT_ID}
        if caption:
            data['caption'] = caption
            data['parse_mode'] = parse_mode

        resp = requests.post(url, data=data, files=files, timeout=15)
        if resp.status_code == 200:
            logger.info("Telegram photo sent successfully")
            return True
        else:
            logger.warning(f"Telegram photo send failed: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Exception while sending Telegram photo: {e}")
        return False
