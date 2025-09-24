import asyncio
import random
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import Message
from pymongo import MongoClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
import time, psutil
from datetime import datetime, timedelta, timezone
import threading
from telegram.ext import Application
from datetime import datetime
import logging
from typing import Dict, Any, List, Optional
from telegram.ext import MessageHandler, filters
from telegram import InputMediaAnimation
import random

# ---------------- Config ---------------- #
BOT_TOKEN = "8306449917:AAH5pJNXixpsRvWlhq4S8BOclX3-tU1DFw8"
OWNER_ID = 5621201759
NOTIFY_CHAT_ID = -1002526806268
MONGO_URI = "mongodb://GoddessAloda:Rrahaman0000@ac-79ttoar-shard-00-00.i3dptoa.mongodb.net:27017,ac-79ttoar-shard-00-01.i3dptoa.mongodb.net:27017,ac-79ttoar-shard-00-02.i3dptoa.mongodb.net:27017/?ssl=true&replicaSet=atlas-pk19pw-shard-0&authSource=admin&retryWrites=true&w=majority&appName=FuckYouKutti"

ACCOUNTS_PER_PAGE = 15
BOT_START_TIME = time.time()
API_ID = 24561470
API_HASH = "1e2d3c0c1fd09ae41a710d2daea8374b"
from telethon import events
from asyncio import sleep as zzz, create_task, CancelledError
from random import randint

# Safari configuration
  # The chat where safari commands are sent

# Dictionary to track safari status for each account
       # Format: {f"{user_id}_{account_name}": {"running": bool, "task": asyncio.Task, "client": TelegramClient}}

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mongo_client = MongoClient(MONGO_URI)
db = mongo_client["telegram_bot_db"]

# Create indexes for better performance
db["auth_users"].create_index("user_id", unique=True)
db["banned_users"].create_index("user_id", unique=True)
db["logs"].create_index([("user_id", 1), ("time", -1)])

# Dictionary to track login sessions
login_sessions = {}

# ---------------- Telethon Utility Functions ---------------- #
async def send_code_telethon(phone: str) -> dict:
    """Send verification code using Telethon"""
    client = TelegramClient(f"session_{int(time.time())}", API_ID, API_HASH)
    await client.connect()
    
    try:
        result = await client.send_code_request(phone)
        return {
            "client": client,
            "phone_code_hash": result.phone_code_hash
        }
    except Exception as e:
        await client.disconnect()
        raise e

async def sign_in_telethon(client: TelegramClient, phone: str, code: str, phone_code_hash: str) -> bool:
    """Sign in with code using Telethon and return True if successful, False if password needed"""
    try:
        # Sign in with the code
        result = await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
        
        # If we get here without exception, sign-in was successful
        print(f"🔧 Debug: Sign-in successful for {phone}")
        return False  # No password needed
        
    except SessionPasswordNeededError:
        print(f"🔧 Debug: 2FA password required for {phone}")
        return True  # Password needed
        
    except Exception as e:
        print(f"🔧 Debug: Sign-in failed for {phone}: {e}")
        raise e  # Re-raise other exceptions

async def check_password_telethon(client: TelegramClient, password: str) -> bool:
    """Check 2FA password using Telethon"""
    try:
        await client.sign_in(password=password)
        return True
    except Exception as e:
        raise e

async def export_session_string_telethon(client: TelegramClient) -> str:
    """Reliable session export that works for both OTP and password logins"""
    try:
        print("🔧 Debug: Starting session export...")
        
        # Ensure connection and authorization
        if not client.is_connected():
            await client.connect()
        
        # Verify we're authorized
        if not await client.is_user_authorized():
            raise Exception("Client not authorized")
        
        # Get user info to confirm login worked
        me = await client.get_me()
        print(f"🔧 Debug: Exporting session for: {me.first_name or 'Unknown'}")
        
        # **METHOD 1: Use Telethon's StringSession (most reliable)**
        try:
            from telethon.sessions import StringSession
            
            # Create a new string session from the current client's session
            string_session = StringSession()
            
            # Save the current session to string format
            session_string = client.session.save()
            
            if session_string and len(session_string) > 100:
                print(f"🔧 Debug: Method 1 successful: {len(session_string)} chars")
                return session_string
                
        except Exception as e:
            print(f"🔧 Debug: Method 1 failed: {e}")
        
        # **METHOD 2: Manual session transfer**
        try:
            from telethon.sessions import StringSession
            
            # Create a new client with StringSession and transfer the auth key
            string_session = StringSession()
            new_client = TelegramClient(string_session, API_ID, API_HASH)
            
            await new_client.connect()
            
            # Transfer the auth key manually
            if hasattr(client.session, 'auth_key') and client.session.auth_key:
                new_client.session.auth_key = client.session.auth_key
                new_client._auth_key = client.session.auth_key
                
                # Verify the new client works
                if await new_client.is_user_authorized():
                    session_string = string_session.save()
                    await new_client.disconnect()
                    
                    if session_string and len(session_string) > 100:
                        print(f"🔧 Debug: Method 2 successful: {len(session_string)} chars")
                        return session_string
                        
            await new_client.disconnect()
            
        except Exception as e:
            print(f"🔧 Debug: Method 2 failed: {e}")
        
        # **METHOD 3: Direct session file extraction**
        try:
            if hasattr(client.session, 'filename') and client.session.filename:
                import os
                if os.path.exists(client.session.filename):
                    with open(client.session.filename, 'r') as f:
                        content = f.read().strip()
                    if content and len(content) > 100:
                        print(f"🔧 Debug: Method 3 successful: {len(content)} chars")
                        return content
        except Exception as e:
            print(f"🔧 Debug: Method 3 failed: {e}")
        
        # **METHOD 4: Last resort - recreate session**
        try:
            from telethon.sessions import StringSession
            import base64
            
            # Get the auth key directly
            auth_key = getattr(client.session, 'auth_key', None)
            if auth_key:
                # Create a proper string session
                string_session = StringSession()
                string_session.set_dc(
                    client.session.dc_id,
                    client.session.server_address,
                    client.session.port
                )
                string_session.auth_key = auth_key
                
                session_string = string_session.save()
                if session_string and len(session_string) > 100:
                    print(f"🔧 Debug: Method 4 successful: {len(session_string)} chars")
                    return session_string
                    
        except Exception as e:
            print(f"🔧 Debug: Method 4 failed: {e}")
        
        raise Exception("All session export methods failed")
        
    except Exception as e:
        print(f"🔧 Debug: Session export error: {e}")
        raise Exception(f"Session export failed: {e}")
        
        

async def recover_session(user_id: int, phone: str):
    """Try to recover session by re-logging in"""
    try:
        # This would need to be implemented based on your specific setup
        # For now, just return a message
        return "Session recovery not implemented. Please login again with /login"
    except Exception as e:
        return f"Recovery failed: {e}"
# ---------------- Decorators ---------------- #
def banned_handler(handler):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id

        # 🚫 Check if banned
        if db["banned_users"].find_one({"user_id": user_id}):
            await update.message.reply_text("❌ You are banned from using this bot.")
            return

        # ✅ Ensure user exists in db["users"]
        ensure_user(
            user_id,
            user.username or user.first_name,
            status="auth"
        )

        # ✅ Log command usage
        log_collection = db["logs"]
        log_collection.insert_one({
            "user_id": user_id,
            "command": update.message.text.split()[0] if update.message else "unknown",
            "time": datetime.now(timezone.utc)
        })

        # Run actual handler
        await handler(update, context)

    return wrapper

def owner_only(handler):
    """Decorator to restrict commands to bot owner only"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        
        # Check if user is owner
        if user_id != OWNER_ID:
            await update.message.reply_text("❌ This command is restricted to bot owner only.")
            return
            
        # Owner is always authorized and can't be banned for these commands
        await handler(update, context)
        
    return wrapper

def authorized_only(handler):
    """Decorator to check if user is authorized and not banned"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_id = user.id
        
        # Check if banned
        if is_banned(user_id):
            await update.message.reply_text("❌ You are banned from using this bot.")
            return

        # Check if authorized
        if not check_authorized(user_id):
            # Notify owner about unauthorized access attempt
            msg_text = (
                f"❌ Unauthorized user tried to use command!\n\n"
                f"Name: {user.full_name}\n"
                f"Username: @{user.username or 'N/A'}\n"
                f"User ID: `{user_id}`\n"
                f"Command: {update.message.text if update.message else 'Unknown'}\n\n"
                f"Use `/auth {user_id}` to authorize."
            )
            
            try:
                sent_msg = await context.bot.send_message(
                    chat_id=OWNER_ID,
                    text=msg_text,
                    parse_mode='Markdown'
                )
                await context.bot.pin_chat_message(chat_id=OWNER_ID, message_id=sent_msg.message_id)
            except Exception as e:
                logger.error(f"Failed to notify owner: {e}")
            
            await update.message.reply_text(
                "❌ You are not authorized to use this bot yet.\n"
                "Your details have been sent to owner for authorization 🫧"
            )
            return

        # Ensure user exists in database
        ensure_user(
            user_id,
            user.username or user.first_name or "Unknown",
            status="auth"
        )

        # Log command usage
        try:
            db["logs"].insert_one({
                "user_id": user_id,
                "command": update.message.text.split()[0] if update.message and update.message.text else "unknown",
                "time": datetime.now(timezone.utc),
                "username": user.username or "N/A"
            })
        except Exception as e:
            logger.error(f"Error logging command: {e}")

        # Run actual handler
        await handler(update, context)

    return wrapper

# ---------------- Utility Functions ---------------- #
def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def user_collection(user_id: int):
    return db[f"user_{user_id}"]

async def notify_owner(context: ContextTypes.DEFAULT_TYPE, text: str):
    try:
        await context.bot.send_message(chat_id=OWNER_ID, text=text)
    except Exception as e:
        logger.error(f"Failed to notify owner: {e}")

def check_authorized(user_id: int) -> bool:
    """Single source of truth for authorization check"""
    try:
        return db["auth_users"].find_one({"user_id": user_id}) is not None
    except Exception as e:
        logger.error(f"Error checking authorization for user {user_id}: {e}")
        return False

def is_banned(user_id: int) -> bool:
    """Check if user is banned"""
    try:
        return db["banned_users"].find_one({"user_id": user_id}) is not None
    except Exception as e:
        logger.error(f"Error checking ban status for user {user_id}: {e}")
        return False

def ensure_user(user_id: int, username: str, status: str = "auth"):
    """Ensure the user exists in users collection with given status."""
    try:
        db["users"].update_one(
            {"_id": user_id},
            {"$set": {"username": username, "status": status, "last_seen": datetime.now(timezone.utc)}},
            upsert=True
        )
    except Exception as e:
        logger.error(f"Error ensuring user {user_id}: {e}")

async def cleanup_login_session(user_id: int):
    """Clean up login session resources"""
    try:
        if user_id in login_sessions:
            session_data = login_sessions[user_id]
            if 'client' in session_data:
                client = session_data['client']
                if isinstance(client, TelegramClient):
                    await client.disconnect()
            login_sessions.pop(user_id, None)
    except Exception as e:
        logger.error(f"Error cleaning up login session for user {user_id}: {e}")
        
async def verify_session(session_string: str) -> bool:
    """Verify if a session string is valid"""
    try:
        from telethon.sessions import StringSession
        
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        # Check if authorized (without raising errors)
        is_auth = await client.is_user_authorized()
        if is_auth:
            me = await client.get_me()
            print(f"🔧 Debug: Session verified for: {me.first_name or 'Unknown'}")
        else:
            print("🔧 Debug: Session verification failed - not authorized")
        
        await client.disconnect()
        return is_auth
        
    except Exception as e:
        print(f"🔧 Debug: Session verification error: {e}")
        return False

# ADD THIS MISSING FUNCTION:
async def get_me_telethon(session_string: str) -> dict:
    """Get user info using Telethon session string"""
    try:
        from telethon.sessions import StringSession
        
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            raise Exception("Session not authorized")
        
        me = await client.get_me()
        
        user_info = {
            'first_name': me.first_name or '',
            'last_name': me.last_name or '',
            'username': me.username or '',
            'user_id': me.id
        }
        
        await client.disconnect()
        return user_info
        
    except Exception as e:
        raise Exception(f"Failed to get user info: {str(e)}")

# ---------------- Telethon-based Commands ---------------- #
@authorized_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"✅ Welcome {user.full_name}!\n"
        f"You are authorized to use this bot.\n"
        f"Use /login <phone_number> to start.\n"
        f"Use /cancel to cancel any ongoing login process."
    )

@authorized_only
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check if already in login process
    if user_id in login_sessions:
        await update.message.reply_text(
            "❌ Login process already in progress.\n"
            "Complete it or use /cancel to start over."
        )
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /login <phone_number>")
        return

    phone = context.args[0]
    
    try:
        # Use Telethon to send code
        result = await send_code_telethon(phone)
        
        # Store login session data
        login_sessions[user_id] = {
            'client': result['client'],
            'phone': phone,
            'phone_code_hash': result['phone_code_hash'],
            'login_start_time': time.time()
        }
        
        await update.message.reply_text(
            "📲 Confirmation code sent! Reply with /otp <code>\n"
            "Use /cancel to cancel this process."
        )
        
    except FloodWaitError as e:
        await update.message.reply_text(f"❌ Flood wait: Please wait {e.seconds} seconds before trying again.")
        await cleanup_login_session(user_id)
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send code: {e}")
        await cleanup_login_session(user_id)

@authorized_only
async def otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check login session
    if user_id not in login_sessions:
        await update.message.reply_text("❌ No login in progress. Use /login <phone>")
        return
        
    session_data = login_sessions[user_id]
    
    # Check login session timeout (10 minutes)
    if time.time() - session_data['login_start_time'] > 600:
        await update.message.reply_text("❌ Login session expired. Please start over with /login")
        await cleanup_login_session(user_id)
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /otp <code>")
        return

    code = context.args[0]
    client = session_data['client']
    phone = session_data['phone']
    phone_code_hash = session_data['phone_code_hash']

    try:
        
    # Use Telethon to sign in
        print(f"🔧 Debug: Attempting sign-in for {phone} with code {code}")
        needs_password = await sign_in_telethon(client, phone, code, phone_code_hash)
        
        if needs_password:
            await update.message.reply_text(
                "🔒 2FA detected! Reply with /password <your_password>\n"
                "Use /cancel to cancel this process."
            )
            return
            
        # Login successful - verify we're authorized before exporting session
        print(f"🔧 Debug: Checking if client is authorized...")
        is_authorized = await client.is_user_authorized()
        print(f"🔧 Debug: Client authorized: {is_authorized}")
        
        if not is_authorized:
            raise Exception("Client failed to authorize after sign-in")
            
        # Get session string
        print(f"🔧 Debug: Attempting to export session for {phone}")
        session_str = await export_session_string_telethon(client)
        print(f"🔧 Debug: Session string length: {len(session_str)}")
    
    # Rest of your code remains the same...
        
        col = user_collection(user_id)
        
        # Get next account number
        acc_count = col.count_documents({})
        acc_num = f"acc{acc_count + 1}"
        
        # Save account with proper order
        account_data = {
            "account": acc_num,
            "account_name": acc_num,
            "phone": phone,
            "session": session_str,
            "tg_name": "",  # Will be fetched later
            "NOTIFY_CHAT_ID": NOTIFY_CHAT_ID,
            "_order": acc_count,
            "created_at": datetime.now(timezone.utc)
        }
        
        result = col.insert_one(account_data)
        print(f"🔧 Debug: Database insert result - inserted_id: {result.inserted_id}")
        
        # Verify the session was saved
        saved_account = col.find_one({"_id": result.inserted_id})
        # Verify the session works
        print("🔧 Debug: Verifying session...")
        is_valid = await verify_session(session_str)
        print(f"🔧 Debug: Session valid: {is_valid}")
        
        if not is_valid:
            await update.message.reply_text("❌ Session validation failed. Please try logging in again.")
            # Remove the invalid account
            col.delete_one({"_id": result.inserted_id})
            await cleanup_login_session(user_id)
            return
        if saved_account and saved_account.get('session'):
            session_saved = len(saved_account['session']) > 50
            print(f"🔧 Debug: Session saved to DB: {session_saved}")
        else:
            print("🔧 Debug: Session NOT saved to DB!")
        
        await update.message.reply_text(f"✅ Logged in {acc_num} successfully! Session saved.")
        await notify_owner(context, f"User {user_id} logged in {phone} as {acc_num}")
        
    except Exception as e:
        error_msg = f"❌ OTP failed: {e}"
        print(f"🔧 Debug Error: {error_msg}")
        await update.message.reply_text(error_msg)
    
    await cleanup_login_session(user_id)

@authorized_only
async def password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in login_sessions:
        await update.message.reply_text("❌ No login in progress.")
        return
        
    session_data = login_sessions[user_id]
    
    if time.time() - session_data['login_start_time'] > 600:
        await update.message.reply_text("❌ Login session expired.")
        await cleanup_login_session(user_id)
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /password <password>")
        return

    pw = context.args[0]
    client = session_data['client']
    phone = session_data['phone']

    try:
        # Sign in with password
        await client.sign_in(password=pw)
        
        # Verify login worked
        me = await client.get_me()
        print(f"✅ Logged in as: {me.first_name}")
        
        # Small delay to ensure everything is settled
        await asyncio.sleep(2)
        
        # **Export session with retry logic**
        max_retries = 3
        session_str = None
        
        for attempt in range(max_retries):
            try:
                print(f"🔧 Debug: Session export attempt {attempt + 1}")
                session_str = await export_session_string_telethon(client)
                if session_str and len(session_str) > 100:
                    print(f"✅ Session export successful: {len(session_str)} chars")
                    break
                else:
                    print(f"❌ Session export returned invalid string: {session_str}")
            except Exception as e:
                print(f"❌ Session export attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)  # Wait before retry
        
        if not session_str or len(session_str) < 100:
            raise Exception("Failed to export valid session after multiple attempts")
        
        # Save to database
        col = user_collection(user_id)
        acc_count = col.count_documents({})
        acc_num = f"acc{acc_count + 1}"
        
        account_data = {
            "account": acc_num,
            "account_name": acc_num,
            "phone": phone,
            "session": session_str,
            "tg_name": me.first_name or "",
            "NOTIFY_CHAT_ID": NOTIFY_CHAT_ID,
            "_order": acc_count,
            "created_at": datetime.now(timezone.utc)
        }
        
        result = col.insert_one(account_data)
        
        # Verify the session was saved
        saved_account = col.find_one({"_id": result.inserted_id})
        if not saved_account or not saved_account.get('session'):
            raise Exception("Session not saved to database")
        
        print(f"🔧 Debug: Session successfully saved to DB for {acc_num}")
        
        await update.message.reply_text(f"✅ Logged in {acc_num} successfully! Session saved.")
        await notify_owner(context, f"User {user_id} logged in {phone} as {acc_num}")
        
    except Exception as e:
        error_msg = f"❌ Password failed: {e}"
        print(f"🔧 Debug Error: {error_msg}")
        await update.message.reply_text(error_msg)
        # Clean up any partial account data
        try:
            col = user_collection(user_id)
            col.delete_one({"phone": phone})
        except:
            pass
    
    finally:
        await cleanup_login_session(user_id)
    
    
@authorized_only
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel ongoing login process"""
    user_id = update.effective_user.id
    await cleanup_login_session(user_id)
    await update.message.reply_text("✅ Login process cancelled successfully.")

# ---------------- Account Management Commands ---------------- #
@authorized_only
async def accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    col = user_collection(user_id)
    
    try:
        accounts_list = list(col.find({}).sort("_order", 1))
    except Exception as e:
        logger.error(f"Error fetching accounts for user {user_id}: {e}")
        await update.message.reply_text("❌ Error fetching accounts.")
        return

    if not accounts_list:
        await update.message.reply_text("❌ You have no logged-in accounts.")
        return

    # Handle pagination
    page = int(context.args[0]) if context.args and context.args[0].isdigit() else 0

    start = page * ACCOUNTS_PER_PAGE
    end = start + ACCOUNTS_PER_PAGE
    accounts_page = accounts_list[start:end]

    msg = "🫧 Your accounts:\n\n"
    for idx, acc in enumerate(accounts_page, start=1):
        account_name = acc.get('account_name', acc['account'])
        msg += f"{start + idx}. {account_name} - {acc['phone']}\n"

    # Pagination buttons
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"accounts_{page-1}"))
    if end < len(accounts_list):
        buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"accounts_{page+1}"))

    reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None
    await update.message.reply_text(msg, reply_markup=reply_markup)

@authorized_only
async def change_acc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /change_acc <current_number> <new_number>")
        return

    current_num, new_num = context.args[0], context.args[1]

    if not new_num.isdigit() or not current_num.isdigit():
        await update.message.reply_text("❌ Both numbers must be numeric.")
        return

    new_acc_name = f"acc{new_num}"
    current_acc_name = f"acc{current_num}"

    col = user_collection(user_id)
    
    # Check if new account name already exists
    if col.find_one({"account": new_acc_name}):
        await update.message.reply_text("❌ Account with this number already exists.")
        return

    # Find and update the account
    result = col.update_one(
        {"account": current_acc_name},
        {"$set": {"account": new_acc_name, "account_name": new_acc_name}}
    )

    if result.modified_count > 0:
        await update.message.reply_text(f"✅ Account {current_acc_name} changed to {new_acc_name} successfully!")
    else:
        await update.message.reply_text("❌ Account not found.")

@authorized_only
async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    col = user_collection(user_id)
    
    try:
        accounts_list = list(col.find({}))
    except Exception as e:
        logger.error(f"Error fetching accounts for ordering: {e}")
        await update.message.reply_text("❌ Error fetching accounts.")
        return

    if not accounts_list:
        await update.message.reply_text("❌ You have no accounts to order.")
        return

    # Sort by numeric part of account name
    def get_account_number(acc):
        try:
            return int(acc["account"][3:])  # Extract number from "accX"
        except (ValueError, IndexError):
            return float('inf')  # Put invalid formats at the end

    sorted_accounts = sorted(accounts_list, key=get_account_number)

    # Update order in database
    try:
        for index, acc in enumerate(sorted_accounts):
            col.update_one({"_id": acc["_id"]}, {"$set": {"_order": index}})
        
        await update.message.reply_text("✅ Accounts have been sorted in ascending order.")
    except Exception as e:
        logger.error(f"Error updating account order: {e}")
        await update.message.reply_text("❌ Error updating account order.")

@authorized_only
async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    col = user_collection(user_id)
    
    try:
        accounts_list = list(col.find({}))
    except Exception as e:
        logger.error(f"Error fetching accounts for logout: {e}")
        await update.message.reply_text("❌ Error fetching accounts.")
        return

    if not accounts_list:
        await update.message.reply_text("❌ You have no accounts logged in.")
        return

    if not context.args:
        # Show accounts list
        msg = "📒 Your logged-in accounts:\n\n"
        for acc in accounts_list:
            msg += f"• {acc['account']} - {acc['phone']}\n"
        msg += "\nUse /logout <acc_number_or_phone> to log out a specific account."
        await update.message.reply_text(msg)
        return

    target = context.args[0]
    acc_to_logout = None
    
    for acc in accounts_list:
        if acc["account"] == target or acc["phone"] == target:
            acc_to_logout = acc
            break

    if not acc_to_logout:
        await update.message.reply_text("❌ No matching account found.")
        return

    # Delete the account
    try:
        col.delete_one({"_id": acc_to_logout["_id"]})
        await update.message.reply_text(
            f"✅ Logged out {acc_to_logout['account']} ({acc_to_logout['phone']}) successfully!"
        )
    except Exception as e:
        logger.error(f"Error logging out account: {e}")
        await update.message.reply_text("❌ Error logging out account.")

# ---------------- Admin Commands ---------------- #

@authorized_only
async def start_safari(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start safari for all accounts"""
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ Only the owner can use this command.")
        return
        
    col = user_collection(user_id)
    accounts_list = list(col.find({}))
    
    if not accounts_list:
        await update.message.reply_text("❌ You have no logged-in accounts.")
        return
        
    started_count = 0
    for account in accounts_list:
        result = await start_safari_for_account(user_id, account['account'], account['session'])
        if "Started" in result:
            started_count += 1
            
    await update.message.reply_text(f"✅ Started safari for {started_count} accounts!")

@authorized_only
async def stop_safari(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop safari for all accounts"""
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ Only the owner can use this command.")
        return
        
    col = user_collection(user_id)
    accounts_list = list(col.find({}))
    
    if not accounts_list:
        await update.message.reply_text("❌ You have no logged-in accounts.")
        return
        
    stopped_count = 0
    for account in accounts_list:
        result = await stop_safari_for_account(user_id, account['account'])
        if "Stopped" in result:
            stopped_count += 1
            
    await update.message.reply_text(f"🛑 Stopped safari for {stopped_count} accounts!")

@authorized_only
async def solo_start_safari(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start safari for a specific account"""
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ Only the owner can use this command.")
        return
        
    if not context.args:
        await update.message.reply_text("❌ Usage: /solo_start_safari <account_number_or_phone>")
        return
        
    target = context.args[0]
    col = user_collection(user_id)
    
    # Properly retrieve the account with session
    account_to_start = col.find_one({
        "$or": [
            {"account": target},
            {"phone": target}
        ]
    })
            
    if not account_to_start:
        await update.message.reply_text("❌ No matching account found.")
        return
    
    # Debug: Check if session exists and is valid
    session_string = account_to_start.get('session')
    if not session_string or session_string == "None":
        await update.message.reply_text(f"❌ {target}: No valid session found. Please login again with /login.")
        return
        
    # Validate session format (basic check)
    if len(session_string) < 100:  # Session strings are typically long
        await update.message.reply_text(f"❌ {target}: Session appears invalid (too short). Please login again.")
        return
        
    print(f"🔍 Debug: Session string preview for {target}: {session_string[:50]}...")
    
    result = await start_safari_for_account(user_id, account_to_start['account'], session_string)
    await update.message.reply_text(result)

@authorized_only
async def solo_stop_safari(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop safari for a specific account"""
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ Only the owner can use this command.")
        return
        
    if not context.args:
        await update.message.reply_text("❌ Usage: /solo_stop_safari <account_number_or_phone>")
        return
        
    target = context.args[0]
    col = user_collection(user_id)
    accounts_list = list(col.find({}))
    
    account_to_stop = None
    for acc in accounts_list:
        if acc["account"] == target or acc["phone"] == target:
            account_to_stop = acc
            break
            
    if not account_to_stop:
        await update.message.reply_text("❌ No matching account found.")
        return
        
    result = await stop_safari_for_account(user_id, account_to_stop['account'])
    await update.message.reply_text(result)

@authorized_only
async def safari_status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check safari status for all accounts"""
    user_id = update.effective_user.id
    col = user_collection(user_id)
    accounts_list = list(col.find({}))
    
    if not accounts_list:
        await update.message.reply_text("❌ You have no accounts.")
        return
    
    msg = "🦁 Safari Status:\n\n"
    for acc in accounts_list:
        account_key = f"{user_id}_{acc['account']}"
        status = " Running ✓" if safari_status.get(account_key, {}).get('running') else " Stopped ❌"
        msg += f"• {acc['account']} - {acc['phone']} - {status}\n"
    
    await update.message.reply_text(msg)
    
@authorized_only
async def init_safari_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initialize chat with safari bot for a specific account"""
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ Only the owner can use this command.")
        return
        
    if not context.args:
        await update.message.reply_text("❌ Usage: /init_safari <account_number>")
        return
        
    target = context.args[0]
    col = user_collection(user_id)
    
    account = col.find_one({
        "$or": [
            {"account": target},
            {"phone": target}
        ]
    })
    
    if not account:
        await update.message.reply_text("❌ No matching account found.")
        return
        
    session_string = account.get('session')
    if not session_string:
        await update.message.reply_text(f"❌ {target}: No session found.")
        return
        
    try:
        from telethon.sessions import StringSession
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
        await client.start()
        
        safari_user = await client.get_entity(SAFARI_CHAT_ID)
        start_msg = await client.send_message(safari_user, "/start")
        await asyncio.sleep(2)
        
        # Check if bot responded
        messages = await client.get_messages(safari_user, limit=2)
        if len(messages) > 1:
            await update.message.reply_text(f"✅ {target}: Safari chat initialized successfully!")
        else:
            await update.message.reply_text(f"⚠️ {target}: Sent /start but no response received.")
            
        await client.disconnect()
        
    except Exception as e:
        await update.message.reply_text(f"❌ {target}: Failed to initialize: {str(e)}")
    
@owner_only
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /auth <user_id>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return

    # Get user info
    try:
        user_obj = await context.bot.get_chat(target_id)
        username = user_obj.username or user_obj.first_name or f"Unknown_{target_id}"
    except:
        username = f"Unknown_{target_id}"

    # Update users collection
    ensure_user(target_id, username, status="auth")
    
    # Add to auth_users
    db["auth_users"].update_one(
        {"user_id": target_id},
        {"$set": {"user_id": target_id, "username": username, "authorized_at": datetime.now(timezone.utc)}},
        upsert=True
    )

    await update.message.reply_text(f"✅ User `{target_id}` has been authorized.", parse_mode="Markdown")

@owner_only
async def unauth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or len(context.args) != 1:
        await update.message.reply_text("Usage: /unauth <user_id>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return

    # Update users collection
    user_doc = db["users"].find_one({"_id": target_id})
    username = user_doc.get("username", f"Unknown_{target_id}") if user_doc else f"Unknown_{target_id}"
    ensure_user(target_id, username, status="unauth")
    
    # Remove from auth_users
    db["auth_users"].delete_one({"user_id": target_id})

    await update.message.reply_text(f"✅ User `{target_id}` has been removed from authorized list.", parse_mode="Markdown")

@owner_only
async def authlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        users = list(db["auth_users"].find({}))
    except Exception as e:
        logger.error(f"Error fetching auth list: {e}")
        await update.message.reply_text("❌ Error fetching authorized users.")
        return

    if not users: 
        await update.message.reply_text("❌ No authorized users.") 
        return 
    
    msg = "🫧 Authorized Users:\n\n"
    for u in users:
        uid = u["user_id"]
        username = u.get("username", "N/A")
        escaped_username = username.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        msg += f"• @{escaped_username} - <code>{uid}</code>\n"
    
    await update.message.reply_text(msg, parse_mode="HTML")

@owner_only
async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /ban <user_id>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return

    # Prevent owner from banning themselves
    if target_id == OWNER_ID:
        await update.message.reply_text("❌ You cannot ban yourself (Owner).")
        return

    # Get user info
    try:
        user_obj = await context.bot.get_chat(target_id)
        username = user_obj.username or user_obj.first_name or f"Unknown_{target_id}"
    except:
        username = f"Unknown_{target_id}"

    # Update users collection
    ensure_user(target_id, username, status="banned")

    # Add to banned_users
    db["banned_users"].update_one(
        {"user_id": target_id},
        {"$set": {"user_id": target_id, "username": username, "banned_at": datetime.now(timezone.utc)}},
        upsert=True
    )

    await update.message.reply_text(f"✅ User `{target_id}` has been banned.", parse_mode="Markdown")

@owner_only
async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /unban <user_id>")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return

    # Get user info
    user_doc = db["users"].find_one({"_id": target_id})
    username = user_doc.get("username", f"Unknown_{target_id}") if user_doc else f"Unknown_{target_id}"

    # Update status to auth
    ensure_user(target_id, username, status="auth")

    # Remove from banned_users
    db["banned_users"].delete_one({"user_id": target_id})

    await update.message.reply_text(f"✅ User `{target_id}` has been unbanned.", parse_mode="Markdown")

@owner_only
async def banlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        banned_users = list(db["banned_users"].find({}))
    except Exception as e:
        logger.error(f"Error fetching ban list: {e}")
        await update.message.reply_text("❌ Error fetching banned users.")
        return

    if not banned_users:
        await update.message.reply_text("❌ There are no banned users.")
        return

    msg = "🚫 Banned Users:\n\n"
    for i, user in enumerate(banned_users, start=1):
        username = user.get("username", "NoUsername")
        user_id = user["user_id"]
        msg += f"{i}. {username} - `{user_id}`\n"

    await update.message.reply_text(msg, parse_mode="Markdown")

@owner_only
async def bot_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Users statistics
        total_users = db["users"].count_documents({})
        authorized_users = db["auth_users"].count_documents({})
        banned_users_count = db["banned_users"].count_documents({})

        # Accounts statistics
        total_accounts = 0
        max_accounts = 0
        max_user = None
        
        for col_name in db.list_collection_names():
            if col_name.startswith("user_"):
                try:
                    user_id = int(col_name.split("_")[1])
                    col = db[col_name]
                    count = col.count_documents({})
                    total_accounts += count
                    if count > max_accounts:
                        max_accounts = count
                        max_user = user_id
                except:
                    continue

        avg_accounts = round(total_accounts / total_users, 2) if total_users else 0

        # Activity statistics
        now = datetime.now(timezone.utc)
        last_24h = db["logs"].count_documents({"time": {"$gte": now - timedelta(hours=24)}})
        last_7d = db["logs"].count_documents({"time": {"$gte": now - timedelta(days=7)}})

        # Uptime
        uptime_seconds = int(time.time() - BOT_START_TIME)
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"

        # System stats
        process = psutil.Process()
        memory = process.memory_info().rss // (1024 * 1024)
        cpu = process.cpu_percent(interval=0.5)

        msg = f"""
📊 Bot Statistics:

👥 Users:
     • Total users: {total_users}
     • Authorized: {authorized_users}
     • Banned: {banned_users_count}

📂 Accounts:
     • Total accounts: {total_accounts}
     • Avg per user: {avg_accounts}
     • Max accounts: {max_accounts} (User {max_user})

⚡ Activity:
     • Commands used (24h): {last_24h}
     • Commands used (7d): {last_7d}

🖥 System:
     • Uptime: {uptime_str}
     • Memory usage: {memory} MB
     • CPU load: {cpu}%
"""
        await update.message.reply_text(msg)
        
    except Exception as e:
        logger.error(f"Error generating bot stats: {e}")
        await update.message.reply_text("❌ Error generating statistics.")

@owner_only
async def board(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /board <message>")
        return

    text = " ".join(context.args)
    sent_count = 0

    for col_name in db.list_collection_names():
        if col_name.startswith("user_"):
            try:
                uid = int(col_name.split("_")[1])
                # Check if user is authorized before sending
                if check_authorized(uid) and not is_banned(uid):
                    await context.bot.send_message(chat_id=uid, text=text)
                    sent_count += 1
            except Exception as e:
                logger.error(f"Error sending message to user {uid}: {e}")
                continue

    await update.message.reply_text(f"✅ Broadcast sent to {sent_count} authorized users")

@owner_only
async def msg_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ Usage: /msg <user_id> <message>")
        return

    try:
        uid = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return

    text = " ".join(context.args[1:])

    try:
        await context.bot.send_message(chat_id=uid, text=text)
        await update.message.reply_text(f"✅ Message sent to {uid}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send message: {e}")


# ---------------- Name Management Commands ---------------- #
@authorized_only
async def names(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    col = user_collection(user_id)
    
    try:
        accounts_list = list(col.find({}))
    except Exception as e:
        logger.error(f"Error fetching accounts for names: {e}")
        await update.message.reply_text("❌ Error fetching accounts.")
        return

    if not accounts_list:
        await update.message.reply_text("No accounts found ❌")
        return

    # Sort accounts by numeric part of account name
    def get_account_number(acc):
        try:
            return int(acc["account"][3:])
        except (ValueError, IndexError):
            return float('inf')

    sorted_accounts = sorted(accounts_list, key=get_account_number)

    async def fetch_name_live(acc):
        """Fetch name from Telegram using Telethon and update cache"""
        session_string = acc.get("session")
        account_name = acc.get("account")
        
        if not session_string:
            return account_name, "No session"
            
        try:
            user_info = await get_me_telethon(session_string)
            tg_name = f"{user_info['first_name']} {user_info['last_name']}".strip() or user_info['username'] or "No Name"
            
            # Update in DB
            col.update_one(
                {"_id": acc["_id"]}, 
                {"$set": {"tg_name": tg_name}}
            )
            
            return account_name, tg_name
        except Exception as e:
            logger.error(f"Failed to fetch name for {account_name}: {e}")
            return account_name, f"Error: {str(e)}"

    # Prepare cached names from sorted accounts
    msg_lines = []
    accounts_to_fetch = []
    
    for acc in sorted_accounts:
        tg_name = acc.get("tg_name")
        acc_name = acc.get("account", "Unknown")
        
        if tg_name:
            msg_lines.append(f"• {acc_name} - {tg_name}")
        else:
            accounts_to_fetch.append(acc)

    # Send cached names first
    if msg_lines:
        await update.message.reply_text(
            "📋 Your accounts and Telegram names (sorted):\n\n" + "\n".join(msg_lines)
        )

    # Fetch missing names
    if accounts_to_fetch:
        await update.message.reply_text("🔄 Fetching updated names from Telegram...")
        
        updated_lines = []
        for acc in accounts_to_fetch:
            account_name, tg_name = await fetch_name_live(acc)
            updated_lines.append(f"• {account_name} - {tg_name}")
            await asyncio.sleep(1)  # Rate limiting

        if updated_lines:
            await update.message.reply_text(
                "🫧 Updated names from Telegram:\n\n" + "\n".join(updated_lines)
            )

@authorized_only
async def order_names(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command to reorder accounts by their numbers"""
    user_id = update.effective_user.id
    col = user_collection(user_id)
    
    try:
        accounts_list = list(col.find({}))
    except Exception as e:
        logger.error(f"Error fetching accounts for ordering: {e}")
        await update.message.reply_text("❌ Error fetching accounts.")
        return

    if not accounts_list:
        await update.message.reply_text("❌ You have no accounts to order.")
        return

    # Sort by numeric part of account name
    def get_account_number(acc):
        try:
            return int(acc["account"][3:])
        except (ValueError, IndexError):
            return float('inf')

    sorted_accounts = sorted(accounts_list, key=get_account_number)

    # Update _order field in database
    try:
        for index, acc in enumerate(sorted_accounts):
            col.update_one(
                {"_id": acc["_id"]},
                {"$set": {"_order": index}}
            )
        
        await update.message.reply_text("✅ Accounts have been sorted in ascending order by their numbers.")
    except Exception as e:
        logger.error(f"Error updating account order: {e}")
        await update.message.reply_text("❌ Error updating account order.")

@authorized_only
async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get the NOTIFY_CHAT_ID value"""
    message = f"Current Notify Gc : `{NOTIFY_CHAT_ID}`"
    await update.message.reply_text(message, parse_mode="Markdown")

@authorized_only
async def set_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set NOTIFY_CHAT_ID for a specific account"""
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ Only the owner can use this command.")
        return
        
    if len(context.args) != 2:
        await update.message.reply_text("❌ Usage: /set_chat <chat_id> <acc_number>")
        return
        
    try:
        chat_id = int(context.args[0])
        acc_number = context.args[1]
    except ValueError:
        await update.message.reply_text("❌ Chat ID must be a number.")
        return

    col = user_collection(user_id)
    account = col.find_one({"account": acc_number})
    
    if not account:
        await update.message.reply_text(f"❌ Account {acc_number} not found.")
        return
        
    # Update the account with the new NOTIFY_CHAT_ID
    col.update_one(
        {"account": acc_number},
        {"$set": {"NOTIFY_CHAT_ID": chat_id}}
    )
    
    await update.message.reply_text(
        f"✅ Notify Gc set to `{chat_id}` for account {acc_number}",
        parse_mode="Markdown"
    )

@authorized_only
async def show_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current NOTIFY_CHAT_ID for a specific account"""
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ Only the owner can use this command.")
        return
        
    if len(context.args) != 1:
        await update.message.reply_text("❌ Usage: /show_chat <acc_number>")
        return
        
    acc_number = context.args[0]
    col = user_collection(user_id)
    account = col.find_one({"account": acc_number})
    
    if not account:
        await update.message.reply_text(f"❌ Account {acc_number} not found.")
        return
        
    # Get the NOTIFY_CHAT_ID, default to global NOTIFY_CHAT_ID if not set
    notify_chat_id = account.get("NOTIFY_CHAT_ID", NOTIFY_CHAT_ID)
    
    await update.message.reply_text(
        f"🔔 Account {acc_number} uses notify gc: `{notify_chat_id}`",
        parse_mode="Markdown"
    )

    
import asyncio
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# forward_tasks maps owner_user_id -> {"task": asyncio.Task, "progress_msg": Message, "count": int, "current": int}
forward_tasks = {}

# Use your existing OWNER_ID and NOTIFY_CHAT_ID variables (they must exist)
# OWNER_ID = ...
# NOTIFY_CHAT_ID = ...

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

@owner_only
async def forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only. Reply to a message and run: /forward [count] or /forward <chat_id> [count]
       Default count = 1. If count>1 => ask confirmation."""
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ You are not authorized.")
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("⚠️ Reply to a message with /forward <count> or /forward <chat_id> <count>")
        return

    # parse args
    target_chat = NOTIFY_CHAT_ID
    count = 1
    try:
        if len(context.args) == 1:
            count = max(1, int(context.args[0]))
        elif len(context.args) >= 2:
            target_chat = int(context.args[0])
            count = max(1, int(context.args[1]))
    except Exception as e:
        await update.message.reply_text("❌ Invalid arguments. Usage: /forward OR reply with /forward <count> OR /forward <chat_id> <count>")
        return

    # If just one copy, do it immediately (no confirm)
    if count == 1:
        try:
            await update.message.reply_to_message.copy(chat_id=target_chat)
            await update.message.reply_text("✅ Forwarded 1/1")
        except Exception as e:
            await update.message.reply_text(f"❌ Forward failed: {e}")
        return

    # count > 1 -> ask confirm
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"confirm_forward:{target_chat}:{count}"),
            InlineKeyboardButton("❌ No", callback_data="cancel_forward")
        ]
    ]
    # keep the replied message so the button handler can read it
    context.user_data["forward_message"] = update.message.reply_to_message
    context.user_data["forward_target_chat"] = target_chat
    context.user_data["forward_count"] = count

    await update.message.reply_text(
        f"⚠️ You are about to forward this {count} times.\nProceed?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


@owner_only
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation buttons. Yes => wait 5s, delete confirm msg, start background forwarding.
       No => quick cancel and delete confirmation message after a short delay."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Add owner check here as well for safety
    if not is_owner(user_id):
        await query.edit_message_text("❌ You are not authorized.")
        return

    if query.data.startswith("confirm_forward"):
        try:
            _, target_chat_s, count_s = query.data.split(":")
            target_chat = int(target_chat_s)
            count = int(count_s)
        except Exception:
            await query.edit_message_text("❌ Invalid confirmation data.")
            return

        message = context.user_data.get("forward_message")
        if not message:
            await query.edit_message_text("❌ No message stored to forward.")
            return

        # Edit to waiting text
        try:
            await query.edit_message_text("Sure! — starting in 5 seconds...")
        except:
            pass

        # small countdown (non-blocking visually, but we sleep)
        await asyncio.sleep(5)

        # attempt to delete the confirmation message (tidy up)
        try:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        except Exception:
            pass

        # start background forwarding (returns immediately)
        await start_forwarding_background(context, message, target_chat, count, user_id)

    elif query.data == "cancel_forward":
        try:
            await query.edit_message_text("❌ Forward cancelled.")
        except:
            pass
        await asyncio.sleep(2)
        try:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
        except:
            pass


async def start_forwarding_background(context: ContextTypes.DEFAULT_TYPE,
                                      message: Message,
                                      target_chat: int,
                                      count: int,
                                      owner_user_id: int):
    """Start the forward loop in a background task and return immediately.
       The background task edits one progress message for updates. Stop instantly by cancelling the task."""
    # Cancel any previously running task for this owner
    existing = forward_tasks.get(owner_user_id)
    if existing and existing.get("task") and not existing["task"].done():
        try:
            existing["task"].cancel()
        except:
            pass

    # Reserve entry before starting task to avoid race
    forward_tasks[owner_user_id] = {"task": None, "progress_msg": None, "count": count, "current": 0}

    async def run():
        # send initial progress message to owner (so they can see edits)
        try:
            progress_msg = await context.bot.send_message(chat_id=owner_user_id, text=f"📤 Forwarding 0/{count}")
            forward_tasks[owner_user_id]["progress_msg"] = progress_msg
        except Exception as e:
            logger.error(f"Failed to create progress message: {e}")
            forward_tasks.pop(owner_user_id, None)
            return

        try:
            for i in range(count):
                # copy the replied message to target chat
                await message.copy(chat_id=target_chat)

                # update counters
                forward_tasks[owner_user_id]["current"] = i + 1

                # edit the progress message (in-place)
                try:
                    await progress_msg.edit_text(f"📤 Forwarding {i+1}/{count}")
                except Exception:
                    # ignore edit failures (message may be deleted)
                    pass

                # wait between forwards (2s)
                await asyncio.sleep(2)

            # finished normally
            try:
                await progress_msg.edit_text(f"✅ Completed {count}/{count}")
            except Exception:
                pass

        except asyncio.CancelledError:
            # immediate cancellation path — edit progress (if exists)
            data = forward_tasks.get(owner_user_id, {})
            prog = data.get("progress_msg")
            current = data.get("current", 0)
            total = data.get("count", count)
            if prog:
                try:
                    await prog.edit_text(f"🫧 Cancelled at {current}/{total}")
                except Exception:
                    pass
            raise

        except Exception as e:
            logger.exception("Error during forwarding task: %s", e)
            prog = forward_tasks.get(owner_user_id, {}).get("progress_msg")
            if prog:
                try:
                    await prog.edit_text(f"❌ Error: {str(e)[:120]}")
                except Exception:
                    pass

        finally:
            # cleanup mapping (task done or cancelled)
            forward_tasks.pop(owner_user_id, None)

    # create and store background task (do NOT await it here)
    task = asyncio.create_task(run())
    forward_tasks[owner_user_id]["task"] = task
    # return immediately so handler doesn't block

@owner_only
async def stop_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only. Immediately stop ongoing forward task and edit the progress message."""
    user_id = update.effective_user.id
    if not is_owner(user_id):
        await update.message.reply_text("❌ You are not authorized.")
        return

    data = forward_tasks.get(user_id)
    if not data or not data.get("task"):
        await update.message.reply_text("⚠️ No active forwarding task.")
        return

    task = data["task"]
    if task.done():
        await update.message.reply_text("⚠️ No active forwarding task.")
        # cleanup if still present
        forward_tasks.pop(user_id, None)
        return

    # Cancel the task immediately
    task.cancel()

    # Wait a short moment to let the task catch CancelledError and edit the progress message
    # but do not block long — we return instantly to the owner
    await asyncio.sleep(0.05)
    await update.message.reply_text("🫧 Forwarding task stopped ")

# ---------------- Callback Query Handler ---------------- #
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    # Handle accounts pagination
    if data.startswith("accounts_"):
        try:
            page = int(data.split("_")[1])
            col = user_collection(user_id)
            accounts_list = list(col.find({}).sort("_order", 1))
            
            start = page * ACCOUNTS_PER_PAGE
            end = start + ACCOUNTS_PER_PAGE
            accounts_page = accounts_list[start:end]
            
            msg = "🫧 Your accounts:\n\n"
            for idx, acc in enumerate(accounts_page, start=1):
                account_name = acc.get('account_name', acc['account'])
                msg += f"{start + idx}. {account_name} - {acc['phone']}\n"
            
            # Pagination buttons
            buttons = []
            if page > 0:
                buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"accounts_{page-1}"))
            if end < len(accounts_list):
                buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"accounts_{page+1}"))
            
            reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None
            
            await query.edit_message_text(msg, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error handling accounts callback: {e}")
            await query.edit_message_text("❌ Error updating accounts list.")


#SAFARI LOGIC BIGINS FROM HERE



#SAFARI LOGIC - FIXED VERSION
#SAFARI LOGIC - FIXED FOR USER CHATS

# Safari configuration - FIXED
SAFARI_BOT_USERNAME = "@HeXamonbot"  # Use username instead of ID
POKEMON_LIST = [
    "Mewtwo", "Ho-Oh", "Lugia", "Kyogre", "Groudon", "Jirachi", "Deoxys", "Arceus", "Dialga", "Palkia",
    "Giratina", "Regigigas", "Heatran", "Genesect", "Kyurem", "Reshiram", "Zekrom", "Victini", "Cobalion",
    "Meloetta", "Hoopa", "Diancie", "Zygarde", "Volcanion", "Necrozma", "Zeraora", "Marshadow", "Magearna",
    "Pheromosa", "Buzzwole", "Guzzlord", "Kubfu", "Glastrier", "Spectrier", "Zacian", "Zamazenta", "Eternatus",
    "Celebi", "Rayquaza", "Shaymin", "Yveltal", "Xerneas", "Cosmog", "Cosmoem", "Solgaleo", "Lunala"
]

# Dictionary to track safari status for each account
safari_status = {}  # Format: {f"{user_id}_{account_name}": {"running": bool, "task": asyncio.Task, "client": TelegramClient}}

async def start_safari_for_account(user_id: int, account_name: str, session_string: str):
    """Start safari hunting for a specific account - FIXED VERSION"""
    account_key = f"{user_id}_{account_name}"
    
    if account_key in safari_status and safari_status[account_key].get('running'):
        return f"❌ {account_name} is already doing safari!"
    
    if not session_string or session_string == "None":
        return f"❌ {account_name}: Invalid session string. Please login again."
    
    try:
        from telethon.sessions import StringSession
        
        client = TelegramClient(
            session=StringSession(session_string),
            api_id=API_ID, 
            api_hash=API_HASH
        )
        
        await client.start()
        
        # Verify connection
        me = await client.get_me()
        if not me:
            return f"❌ {account_name}: Failed to authenticate session."
        
        print(f"✅ {account_name}: Successfully connected as {me.first_name}")
        
        # **FIXED: Get bot entity by username**
        try:
            safari_bot = await client.get_entity(SAFARI_BOT_USERNAME)
            print(f"✅ {account_name}: Safari bot entity loaded - {safari_bot.username}")
            
        except Exception as e:
            print(f"❌ {account_name}: Failed to get safari bot entity: {e}")
            await client.disconnect()
            return f"❌ {account_name}: Cannot find safari bot '{SAFARI_BOT_USERNAME}'. Make sure the bot exists."
        
        # **AUTO-START: Send /start to initialize chat**
        try:
            print(f"🔄 {account_name}: Initializing chat with safari bot...")
            start_msg = await client.send_message(safari_bot, "/start")
            await asyncio.sleep(2)  # Wait for bot response
            
            # Check if bot responded
            messages = await client.get_messages(safari_bot, limit=2)
            if len(messages) > 1:
                print(f"✅ {account_name}: Safari chat initialized successfully!")
            else:
                print(f"⚠️ {account_name}: Sent /start but no response received")
                
        except Exception as e:
            print(f"❌ {account_name}: Failed to initialize chat: {e}")
            await client.disconnect()
            return f"❌ {account_name}: Failed to start chat with safari bot. Error: {str(e)}"
        
        # Store safari status
        safari_status[account_key] = {
            'running': True,
            'client': client,
            'hunt_watchdog': None,
            'user_id': user_id,
            'account_name': account_name,
            'safari_bot': safari_bot  # Store the bot entity
        }
        
        # Setup event handlers
        setup_safari_handlers(client, user_id, account_name, safari_bot)
        
        # Start safari in background
        task = asyncio.create_task(run_safari_hunt(user_id, account_name, client, safari_bot))
        safari_status[account_key]['task'] = task
        
        return f"✅ Started safari for {account_name}!"
        
    except Exception as e:
        error_msg = f"❌ Failed to start safari for {account_name}: {str(e)}"
        print(error_msg)
        
        # Cleanup on failure
        if account_key in safari_status:
            client = safari_status[account_key].get('client')
            if client:
                try:
                    await client.disconnect()
                except:
                    pass
            safari_status.pop(account_key, None)
        
        return error_msg

async def run_safari_hunt(user_id: int, account_name: str, client: TelegramClient, safari_bot):
    """Main safari hunting loop - FIXED"""
    account_key = f"{user_id}_{account_name}"
    
    try:
        print(f"🔰 {account_name}: Starting safari process...")
        
        # Send mystats to begin the process
        await client.send_message(safari_bot, "/mystats")
        print(f"🔰 {account_name}: Checking stats...")
        
        # Wait and then send enter command
        await asyncio.sleep(3)
        await client.send_message(safari_bot, "/enter")
        print(f"🚪 {account_name}: Sent /enter")
        
        # Check entry status with retries
        max_retries = 3
        entered = False
        
        for attempt in range(max_retries):
            await asyncio.sleep(5)
            last_msg = await client.get_messages(safari_bot, limit=1)
            
            if last_msg:
                text = last_msg[0].text.lower() if last_msg[0].text else ""
                if "you have already played the safari game today" in text:
                    print(f"📛 {account_name}: Safari already played today.")
                    await notify_safari_status(user_id, account_name, "Safari already played today")
                    return
                elif "entry fee deducted" in text or "you are already in the" in text or "welcome" in text:
                    print(f"✅ {account_name}: Entered Safari Zone.")
                    entered = True
                    break
                elif "cannot enter" in text or "failed" in text:
                    print(f"❌ {account_name}: Entry failed, retrying...")
                    await client.send_message(safari_bot, "/enter")
                    continue
        
        if not entered:
            print(f"❌ {account_name}: Failed to enter safari after {max_retries} attempts")
            return
        
        # Start hunting
        print(f"🎯 {account_name}: Starting hunt...")
        await send_safari_hunt(client, account_key, safari_bot)
        
        # Main hunting loop
        while safari_status.get(account_key, {}).get('running', False):
            await asyncio.sleep(1)  # Small delay to prevent busy waiting
            
    except Exception as e:
        print(f"❌ {account_name}: Safari error - {e}")
        # Try to send error notification
        try:
            await notify_safari_status(user_id, account_name, f"Error: {str(e)}")
        except:
            pass
    finally:
        # Cleanup
        if account_key in safari_status:
            safari_status[account_key]['running'] = False
            try:
                await client.disconnect()
                print(f"✅ {account_name}: Disconnected successfully")
            except Exception as e:
                print(f"❌ {account_name}: Error during disconnect - {e}")

async def send_safari_hunt(client: TelegramClient, account_key: str, safari_bot):
    """Send hunt command and setup watchdog"""
    if not safari_status.get(account_key, {}).get('running'):
        return
    
    try:
        await client.send_message(safari_bot, "/hunt")
        print(f"🔁 {account_key}: Sent /hunt")
        
        # Cancel previous watchdog
        if safari_status[account_key].get('hunt_watchdog'):
            safari_status[account_key]['hunt_watchdog'].cancel()
        
        # Create new watchdog (15 second timeout)
        safari_status[account_key]['hunt_watchdog'] = asyncio.create_task(safari_hunt_timeout(client, account_key, safari_bot))
    except Exception as e:
        print(f"❌ {account_key}: Failed to send hunt command - {e}")

async def safari_hunt_timeout(client: TelegramClient, account_key: str, safari_bot):
    """Hunt timeout watchdog (15 seconds)"""
    try:
        await asyncio.sleep(15)
        if safari_status.get(account_key, {}).get('running'):
            await send_safari_hunt(client, account_key, safari_bot)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"❌ {account_key}: Watchdog error - {e}")

def setup_safari_handlers(client: TelegramClient, user_id: int, account_name: str, safari_bot):
    """Setup event handlers for safari - FIXED"""
    account_key = f"{user_id}_{account_name}"
    
    @client.on(events.NewMessage(from_users=safari_bot.id, incoming=True))
    async def safari_message_handler(event):
        if not safari_status.get(account_key, {}).get('running'):
            return
        
        text = event.message.text or ""
        message = event.message
        
        print(f"📨 {account_name}: Received - {text[:100]}...")
        
        # Shiny found
        if "✨ shiny pokémon found!" in text.lower():
            print(f"✨ {account_name}: Shiny Pokémon found!")
            await notify_safari_status(user_id, account_name, "✨ Shiny Pokémon found!")
            await stop_safari_for_account(user_id, account_name)
            return
        
        # Daily limit reached
        if "daily hunt limit reached" in text.lower():
            print(f"📛 {account_name}: Daily hunt limit reached")
            await notify_safari_status(user_id, account_name, "📛 Daily hunt limit reached")
            await stop_safari_for_account(user_id, account_name)
            return
        
        # Safari ended
        text_l = text.lower()
        if ("you have run out of safari balls" in text_l and "are now exiting" in text_l) or "you were kicked" in text_l:
            print(f"⚕️ {account_name}: Safari completed")
            await notify_safari_status(user_id, account_name, "⚕️ Safari completed")
            await stop_safari_for_account(user_id, account_name)
            return
        
        # Wild Pokémon encountered
        if text.startswith("A wild"):
            print(f"🎯 {account_name}: Wild Pokémon encountered")
            # Cancel watchdog
            if safari_status[account_key].get('hunt_watchdog'):
                safari_status[account_key]['hunt_watchdog'].cancel()
            
            # Check for rare Pokémon
            matched = False
            for poke in POKEMON_LIST:
                if poke in text:
                    matched = True
                    try:
                        # Try to click buttons
                        await message.click(text="Engage")
                        await asyncio.sleep(1)
                        await message.click(text="Engage")
                        print(f"✅ {account_name}: Engaged with {poke}")
                    except Exception as e:
                        print(f"❌ {account_name}: Engage failed - {e}")
                    break
            
            if not matched:
                print(f"⏩ {account_name}: No rare Pokémon, skipping")
                await asyncio.sleep(random.randint(3, 4))
                if safari_status.get(account_key, {}).get('running'):
                    await send_safari_hunt(client, account_key, safari_bot)
        
        # Ball throwing - look for the initial message with "Throw ball" button
        elif "wild" in text.lower() and "appeared" in text.lower() and "throw ball" in text.lower():
            try:
                await message.click(text="Throw ball")
                print(f"🎯 {account_name}: Threw ball")
            except Exception as e:
                print(f"❌ {account_name}: Throw ball failed - {e}")
    
    @client.on(events.MessageEdited(from_users=safari_bot.id))
    async def safari_message_edited_handler(event):
        if not safari_status.get(account_key, {}).get('running'):
            return
            
        text = event.message.text or ""
        print(f"✏️ {account_name}: Edited message - {text[:100]}...")
        
        # **FIXED: Better detection for ball failure outcomes**
        if any(phrase in text.lower() for phrase in [
            "your safari ball failed", 
            "the wild", 
            "fled",
            "caught a wild",
            "fainted"
            "TM"
            "an expert trainer"
        ]):
            print(f"🔄 {account_name}: Pokémon outcome detected - sending next hunt in 3 seconds")
            await asyncio.sleep(3)  # Wait a bit longer for the animation to complete
            
            if safari_status.get(account_key, {}).get('running'):
                await send_safari_hunt(client, account_key, safari_bot)
        
        # **Also handle retry for failed balls**
        elif "safari ball failed" in text.lower() and "throw ball" in text.lower():
            try:
                await event.message.click(text="Throw ball")
                print(f"🔁 {account_name}: Retried throw ball")
            except Exception as e:
                print(f"❌ {account_name}: Retry failed - {e}")
                
async def notify_safari_status(user_id: int, account_name: str, status: str):
    """Notify about safari status"""
    # You can implement notification logic here
    print(f"📢 {account_name}: {status}")

# Remove the old init_safari_chat function since it's no longer needed
               
@authorized_only
async def debug_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug session information for an account"""
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("❌ Usage: /debug_session <account_number>")
        return
        
    acc_number = context.args[0]
    col = user_collection(user_id)
    account = col.find_one({"account": acc_number})
    
    if not account:
        await update.message.reply_text("❌ Account not found.")
        return
    
    session = account.get('session')
    msg = f"""
🔍 Debug Info for {acc_number}:
• Phone: {account.get('phone', 'N/A')}
• Session exists: {bool(session)}
• Session length: {len(session) if session else 0}
• Session preview: {session[:50] + '...' if session else 'None'}
"""
    await update.message.reply_text(msg)                
    
@authorized_only
async def test_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test if sessions are working"""
    user_id = update.effective_user.id
    col = user_collection(user_id)
    
    accounts = list(col.find({}))
    for acc in accounts:
        session = acc.get('session')
        if session:
            is_valid = await verify_session(session)
            status = "✅ Valid" if is_valid else "❌ Invalid"
            await update.message.reply_text(f"{acc['account']}: {status} (length: {len(session)})")
        else:
            await update.message.reply_text(f"{acc['account']}: ❌ No session")
 


@authorized_only
async def debug_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug login session state"""
    user_id = update.effective_user.id
    
    if user_id not in login_sessions:
        await update.message.reply_text("❌ No active login session")
        return
        
    session_data = login_sessions[user_id]
    client = session_data['client']
    
    try:
        is_connected = client.is_connected()
        is_authorized = await client.is_user_authorized() if is_connected else False
        
        await update.message.reply_text(
            f"🔧 Login Session Debug:\n"
            f"• Connected: {is_connected}\n"
            f"• Authorized: {is_authorized}\n"
            f"• Phone: {session_data['phone']}\n"
            f"• Session age: {int(time.time() - session_data['login_start_time'])}s"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Debug error: {e}") 
        
        
@authorized_only
async def test_my_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test all sessions for the current user"""
    user_id = update.effective_user.id
    col = user_collection(user_id)
    
    accounts = list(col.find({}))
    
    if not accounts:
        await update.message.reply_text("❌ No accounts found")
        return
    
    message = "🔍 Session Test Results:\n\n"
    
    for acc in accounts:
        session = acc.get('session')
        account_name = acc.get('account', 'Unknown')
        
        if not session:
            message += f"❌ {account_name}: No session string\n"
            continue
            
        try:
            from telethon.sessions import StringSession
            client = TelegramClient(StringSession(session), API_ID, API_HASH)
            await client.connect()
            
            if await client.is_user_authorized():
                me = await client.get_me()
                message += f"✅ {account_name}: Working ({me.first_name or 'Unknown'})\n"
            else:
                message += f"❌ {account_name}: Not authorized\n"
                
            await client.disconnect()
            
        except Exception as e:
            message += f"❌ {account_name}: Error - {str(e)[:50]}...\n"
    
    await update.message.reply_text(message)
    
    
@authorized_only
async def session_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get detailed session information"""
    user_id = update.effective_user.id
    
    if user_id not in login_sessions:
        await update.message.reply_text("❌ No active login session")
        return
        
    session_data = login_sessions[user_id]
    client = session_data['client']
    
    try:
        # Get detailed session info
        is_connected = client.is_connected()
        is_authorized = await client.is_user_authorized() if is_connected else False
        
        # Get session details
        session_details = ""
        if hasattr(client.session, 'save'):
            try:
                temp_session = client.session.save()
                session_details = f"Session can be saved: Yes\nLength: {len(temp_session) if temp_session else 0}"
            except:
                session_details = "Session can be saved: No"
        
        if hasattr(client.session, 'auth_key'):
            auth_key = client.session.auth_key
            session_details += f"\nAuth key exists: {auth_key is not None}"
            if auth_key:
                session_details += f"\nAuth key length: {len(auth_key)}"
        
        await update.message.reply_text(
            f"🔧 Detailed Session Info:\n"
            f"• Connected: {is_connected}\n"
            f"• Authorized: {is_authorized}\n"
            f"• Phone: {session_data['phone']}\n"
            f"• Session age: {int(time.time() - session_data['login_start_time'])}s\n"
            f"• {session_details}"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting session info: {e}")
# ---------------- Main Function ---------------- #
def main():
    # Create application
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("login", login))
    application.add_handler(CommandHandler("otp", otp))
    application.add_handler(CommandHandler("password", password))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("accounts", accounts))
    application.add_handler(CommandHandler("change_acc", change_acc))
    application.add_handler(CommandHandler("order", order))
    application.add_handler(CommandHandler("logout", logout))
    application.add_handler(CommandHandler("auth", auth))
    application.add_handler(CommandHandler("unauth", unauth))
    application.add_handler(CommandHandler("authlist", authlist))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("banlist", banlist))
    application.add_handler(CommandHandler("bot_stats", bot_stats))
    application.add_handler(CommandHandler("board", board))
    application.add_handler(CommandHandler("msg", msg_user))
    application.add_handler(CommandHandler("names", names))
    application.add_handler(CommandHandler("order_names", order_names))
    application.add_handler(CommandHandler("get_chat_id", get_chat_id))
    application.add_handler(CommandHandler("show_chat", show_chat))
    # Add the callback query handler with the correct pattern
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(confirm_forward:|cancel_forward)"))
    
    # Your other handlers...
    application.add_handler(CommandHandler("forward", forward))
    application.add_handler(CommandHandler("stop", stop_forward))

    
    application.add_handler(CommandHandler("set_chat", set_chat))

    # Add callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    
    # Add these to your main() function where you register handlers:
    application.add_handler(CommandHandler("start_safari", start_safari))
    application.add_handler(CommandHandler("stop_safari", stop_safari))
    application.add_handler(CommandHandler("solo_start_safari", solo_start_safari))
    application.add_handler(CommandHandler("solo_stop_safari", solo_stop_safari))
    application.add_handler(CommandHandler("safari_status", safari_status_cmd))
    
    # Add to your main() function
    application.add_handler(CommandHandler("debug_session", debug_session))
    
    application.add_handler(CommandHandler("test_session", test_session))
    application.add_handler(CommandHandler("debug_login", debug_login))
    application.add_handler(CommandHandler("test_my_sessions", test_my_sessions))
    application.add_handler(CommandHandler("session_info", session_info))
    application.add_handler(CommandHandler("init_safari", init_safari_chat))

    # Start the bot
    application.run_polling()
    logger.info("Bot started successfully!")

if __name__ == "__main__":

    main()
