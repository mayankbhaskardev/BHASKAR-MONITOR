import sqlite3
import os
from datetime import datetime
import logging

logger = logging.getLogger('monitor_database')

DB_PATH = 'monitoring.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Monitored accounts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitored_accounts (
            username TEXT PRIMARY KEY,
            status TEXT DEFAULT 'unknown',
            last_checked TEXT,
            followers INTEGER DEFAULT 0,
            following INTEGER DEFAULT 0,
            posts INTEGER DEFAULT 0,
            full_name TEXT,
            is_private INTEGER DEFAULT 0,
            is_verified INTEGER DEFAULT 0,
            added_by TEXT,
            channel_id INTEGER
        )
    ''')
    
    # Event logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monitoring_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            username TEXT,
            event_type TEXT,
            message TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

def add_account(username, added_by=None, channel_id=None):
    username = username.strip().lower().lstrip('@')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO monitored_accounts 
            (username, added_by, channel_id, status) 
            VALUES (?, ?, ?, 'unknown')
        ''', (username, str(added_by) if added_by else None, channel_id))
        conn.commit()
        log_event(username, 'info', f"Started monitoring account: @{username}")
        return True
    except Exception as e:
        logger.error(f"Error adding account {username}: {e}")
        return False
    finally:
        conn.close()

def remove_account(username):
    username = username.strip().lower().lstrip('@')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM monitored_accounts WHERE username = ?', (username,))
        conn.commit()
        log_event(username, 'info', f"Stopped monitoring account: @{username}")
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error removing account {username}: {e}")
        return False
    finally:
        conn.close()

def get_monitored_accounts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM monitored_accounts')
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_account(username):
    username = username.strip().lower().lstrip('@')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM monitored_accounts WHERE username = ?', (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_account_state(username, status, followers=0, following=0, posts=0, full_name=None, is_private=0, is_verified=0):
    username = username.strip().lower().lstrip('@')
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    try:
        cursor.execute('''
            UPDATE monitored_accounts 
            SET status = ?, last_checked = ?, followers = ?, following = ?, posts = ?, 
                full_name = ?, is_private = ?, is_verified = ?
            WHERE username = ?
        ''', (status, now, followers, following, posts, full_name, 1 if is_private else 0, 1 if is_verified else 0, username))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating account state for {username}: {e}")
    finally:
        conn.close()

def log_event(username, event_type, message):
    conn = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now().isoformat()
    try:
        cursor.execute('''
            INSERT INTO monitoring_logs (timestamp, username, event_type, message)
            VALUES (?, ?, ?, ?)
        ''', (now, username.lower().lstrip('@') if username else None, event_type, message))
        conn.commit()
    except Exception as e:
        logger.error(f"Error logging event: {e}")
    finally:
        conn.close()

def get_recent_logs(limit=15):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM monitoring_logs ORDER BY timestamp DESC LIMIT ?', (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows
