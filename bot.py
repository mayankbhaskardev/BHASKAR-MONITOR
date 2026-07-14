import discord
from discord.ext import commands
import asyncio
import logging
import sys
import os

# Import local modules
import config
import database
import notifier
import monitor
import commands as bot_commands
import session_manager

# Setup logger
logger = logging.getLogger('discord_bot')

# Initialize Database
database.init_db()

# Setup bot
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Register command handlers
bot_commands.setup_commands(bot)

@bot.event
async def on_ready():
    print("=" * 60)
    print("🚀 INSTAGRAM REAL MONITOR BOT STARTED!")
    print("=" * 60)
    print(f"🤖 Bot Name: {bot.user.name}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"⚡ Latency: {round(bot.latency * 1000)}ms")
    print("=" * 60)
    
    # Initialize dynamic references
    notifier.init_notifier(bot)
    
    # Send start notification to Telegram
    notifier.send_telegram_notification("🚀 <b>Instagram Monitor Bot is now online!</b>")
    
    # Start background monitoring loop (check every 15 minutes)
    asyncio.create_task(monitor.start_monitoring_loop(bot, interval_seconds=900))
    
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="Instagram accounts | !help"
    ))

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument: `{ctx.prefix}{ctx.command.name} {ctx.command.signature}`")
    else:
        logger.error(f"Error executing command: {error}")
        await ctx.send(f"❌ An error occurred: {error}")

if __name__ == '__main__':
    logger.info("Starting Instagram Monitor Bot...")
    
    if not config.DISCORD_TOKEN or config.DISCORD_TOKEN.strip() == "":
        logger.error("Discord Token is missing! Check your credentials.csv or environment variables.")
        sys.exit(1)
        
    try:
        bot.run(config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested.")
    except Exception as e:
        logger.critical(f"Unhandled bot exception: {e}")
    finally:
        # Graceful cleanup of session
        logger.info("Cleaning up session connections...")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(session_manager.close_session())
            else:
                loop.run_until_complete(session_manager.close_session())
        except Exception as cleanup_err:
            logger.error(f"Error during cleanup: {cleanup_err}")