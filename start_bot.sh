#!/data/data/com.termux/files/usr/bin/bash
# Auto-start Discord bot for Termux

# Change to the bot directory
cd "$(dirname "$0")"

# Start the bot and log output
python bot.py >> bot.log 2>&1 