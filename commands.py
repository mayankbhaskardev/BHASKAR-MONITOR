import discord
from discord.ext import commands
import database
import monitor
import config
from datetime import datetime
import logging

logger = logging.getLogger('monitor_commands')

def setup_commands(bot):
    
    @bot.command(name='monitor', description='Start monitoring an Instagram account.')
    async def monitor_cmd(ctx, username: str):
        username = username.strip().lower().lstrip('@')
        if not username:
            await ctx.send("❌ Please provide a valid username.")
            return
            
        existing = database.get_account(username)
        if existing:
            await ctx.send(f"ℹ️ @{username} is already being monitored.")
            return
            
        success = database.add_account(username, added_by=ctx.author.id, channel_id=ctx.channel.id)
        if not success:
            await ctx.send(f"❌ Failed to add @{username} to the database.")
            return
            
        loading_embed = discord.Embed(
            title="⏳ Starting Monitoring...",
            description=f"Added @{username} to list. Running initial status check...",
            color=config.COLORS['warning']
        )
        loading_msg = await ctx.send(embed=loading_embed)
        
        status, data = await monitor.check_account_status(username)
        
        try:
            await loading_msg.delete()
        except Exception:
            pass
            
        if status in ('active', 'banned'):
            database.update_account_state(
                username, 
                status=status,
                followers=data.get('followers', 0),
                following=data.get('following', 0),
                posts=data.get('posts', 0),
                full_name=data.get('full_name'),
                is_private=data.get('is_private', 0),
                is_verified=data.get('is_verified', 0)
            )
            status_color = config.COLORS['success'] if status == 'active' else config.COLORS['danger']
            status_text = "🟢 Active" if status == 'active' else "🔴 Banned / Deleted"
            
            embed = discord.Embed(
                title=f"📡 Monitoring Started: @{username}",
                color=status_color,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="👤 Full Name", value=data.get('full_name') or username, inline=True)
            embed.add_field(name="📊 Initial Status", value=status_text, inline=True)
            embed.add_field(name="👥 Followers", value=f"{data.get('followers', 0):,}", inline=True)
            embed.add_field(name="📸 Posts", value=str(data.get('posts', 0)), inline=True)
            embed.set_footer(text="Instagram Real Monitor")
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"⚠️ Added @{username} to database, but initial check failed (Rate limited or Connection issue). The background task will check it shortly.")

    @bot.command(name='stop', description='Stop monitoring an Instagram account.')
    async def stop_cmd(ctx, username: str):
        username = username.strip().lower().lstrip('@')
        if not username:
            await ctx.send("❌ Please provide a valid username.")
            return
            
        deleted = database.remove_account(username)
        if deleted:
            await ctx.send(f"✅ Stopped monitoring @{username}.")
        else:
            await ctx.send(f"❌ @{username} is not in the monitored accounts list.")

    @bot.command(name='list', description='Show all monitored accounts.')
    async def list_cmd(ctx):
        accounts = database.get_monitored_accounts()
        if not accounts:
            await ctx.send("ℹ️ No accounts are currently being monitored.")
            return
            
        embed = discord.Embed(
            title="📋 Monitored Instagram Accounts",
            color=config.COLORS['primary'],
            timestamp=datetime.utcnow()
        )
        
        description = ""
        for acc in accounts:
            status_icon = "🟢" if acc['status'] == 'active' else "🔴" if acc['status'] == 'banned' else "🟡"
            description += f"{status_icon} **@{acc['username']}** - Followers: {acc['followers']:,} | Last Checked: {acc['last_checked'] or 'Never'}\n"
            
        embed.description = description
        embed.set_footer(text=f"Total: {len(accounts)} accounts")
        await ctx.send(embed=embed)

    @bot.command(name='status', description='Show details of a monitored account.')
    async def status_cmd(ctx, username: str):
        username = username.strip().lower().lstrip('@')
        if not username:
            await ctx.send("❌ Please provide a valid username.")
            return
            
        acc = database.get_account(username)
        if not acc:
            await ctx.send(f"❌ @{username} is not in the monitored accounts list. Use `!monitor` to add it.")
            return
            
        status_color = config.COLORS['success'] if acc['status'] == 'active' else config.COLORS['danger'] if acc['status'] == 'banned' else config.COLORS['warning']
        status_text = "🟢 Active" if acc['status'] == 'active' else "🔴 Banned / Deleted" if acc['status'] == 'banned' else "🟡 Unknown"
        
        embed = discord.Embed(
            title=f"Database Status: @{acc['username']}",
            color=status_color,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="👤 Full Name", value=acc['full_name'] or "N/A", inline=True)
        embed.add_field(name="📊 Status", value=status_text, inline=True)
        embed.add_field(name="👥 Followers", value=f"{acc['followers']:,}", inline=True)
        embed.add_field(name="📸 Posts", value=str(acc['posts']), inline=True)
        embed.add_field(name="🔒 Private", value="Yes" if acc['is_private'] else "No", inline=True)
        embed.add_field(name="✅ Verified", value="Yes" if acc['is_verified'] else "No", inline=True)
        embed.add_field(name="⏰ Last Checked", value=acc['last_checked'] or "Never", inline=False)
        embed.set_footer(text="Instagram Real Monitor")
        
        await ctx.send(embed=embed)

    @bot.command(name='check', description='Perform an immediate check on any account.')
    async def check_cmd(ctx, username: str):
        username = username.strip().lower().lstrip('@')
        if not username:
            await ctx.send("❌ Please provide a valid username.")
            return
            
        loading_msg = await ctx.send(f"🔍 Fetching live status for @{username}...")
        status, data = await monitor.check_account_status(username)
        
        try:
            await loading_msg.delete()
        except Exception:
            pass
            
        if status in ('active', 'banned'):
            # Update DB state if monitored
            existing = database.get_account(username)
            if existing:
                database.update_account_state(
                    username,
                    status=status,
                    followers=data.get('followers', 0),
                    following=data.get('following', 0),
                    posts=data.get('posts', 0),
                    full_name=data.get('full_name'),
                    is_private=data.get('is_private', 0),
                    is_verified=data.get('is_verified', 0)
                )
                
            status_color = config.COLORS['success'] if status == 'active' else config.COLORS['danger']
            status_text = "🟢 Active" if status == 'active' else "🔴 Banned / Deleted"
            
            embed = discord.Embed(
                title=f"Live Check: @{username}",
                color=status_color,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="👤 Full Name", value=data.get('full_name') or username, inline=True)
            embed.add_field(name="📊 Status", value=status_text, inline=True)
            embed.add_field(name="👥 Followers", value=f"{data.get('followers', 0):,}", inline=True)
            embed.add_field(name="📸 Posts", value=str(data.get('posts', 0)), inline=True)
            embed.add_field(name="🔒 Private", value="Yes" if data.get('is_private') else "No", inline=True)
            embed.add_field(name="✅ Verified", value="Yes" if data.get('is_verified') else "No", inline=True)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ Failed to fetch live data for @{username}. Error: {data.get('error', 'Scraper failed')}")

    @bot.command(name='stats', description='Show monitoring statistics.')
    async def stats_cmd(ctx):
        accounts = database.get_monitored_accounts()
        total = len(accounts)
        active = sum(1 for a in accounts if a['status'] == 'active')
        banned = sum(1 for a in accounts if a['status'] == 'banned')
        unknown = sum(1 for a in accounts if a['status'] == 'unknown')
        
        embed = discord.Embed(
            title="📊 Monitoring Statistics",
            color=config.COLORS['dark'],
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="📈 Total Monitored", value=str(total), inline=True)
        embed.add_field(name="🟢 Active Accounts", value=str(active), inline=True)
        embed.add_field(name="🔴 Banned Accounts", value=str(banned), inline=True)
        embed.add_field(name="🟡 Unknown Status", value=str(unknown), inline=True)
        
        await ctx.send(embed=embed)

    @bot.command(name='logs', description='Display recent monitoring events.')
    async def logs_cmd(ctx):
        logs = database.get_recent_logs(15)
        if not logs:
            await ctx.send("ℹ️ No log events recorded yet.")
            return
            
        embed = discord.Embed(
            title="📋 Recent Monitoring Logs",
            color=config.COLORS['purple'],
            timestamp=datetime.utcnow()
        )
        
        log_text = ""
        for log in logs:
            timestamp = log['timestamp'].split('T')[1][:8] if 'T' in log['timestamp'] else log['timestamp']
            event_emoji = "🚨" if log['event_type'] == 'status_change' else "⚠️" if log['event_type'] == 'check_failed' else "ℹ️"
            log_text += f"`{timestamp}` {event_emoji} **{log['username'] or 'system'}**: {log['message']}\n"
            
        embed.description = log_text
        await ctx.send(embed=embed)

    @bot.command(name='help', description='Display all commands.')
    async def help_cmd(ctx):
        embed = discord.Embed(
            title="🤖 Instagram Monitoring Bot Help",
            description="A real-time monitoring service checking Instagram account statuses.",
            color=config.COLORS['purple'],
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="📡 `!monitor <username>`", value="Add a new Instagram account to the monitor list.", inline=False)
        embed.add_field(name="⏹️ `!stop <username>`", value="Stop monitoring an Instagram account.", inline=False)
        embed.add_field(name="📋 `!list`", value="Show all accounts currently being monitored.", inline=False)
        embed.add_field(name="🔍 `!check <username>`", value="Perform an immediate live check on any username.", inline=False)
        embed.add_field(name="📊 `!status <username>`", value="Show details of a monitored account from the database.", inline=False)
        embed.add_field(name="📉 `!stats`", value="Show monitoring system statistics.", inline=False)
        embed.add_field(name="📜 `!logs`", value="Display recent status logs and check failures.", inline=False)
        embed.add_field(name="❓ `!help`", value="Show this help menu.", inline=False)
        
        await ctx.send(embed=embed)
