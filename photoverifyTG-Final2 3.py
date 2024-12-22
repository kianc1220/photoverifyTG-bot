import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

# Dictionary to track new users and their verification status
pending_users = {}

# Replace with your logging group chat ID (can be obtained by adding the bot to the group and using the getUpdates method)
LOGGING_CHAT_ID = '-4761682303'  # Use the actual chat ID of your logging group

# Function to send logs to the logging group
async def send_log(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send log messages to the logging group."""
    try:
        await context.bot.send_message(chat_id=LOGGING_CHAT_ID, text=message)
    except Exception as e:
        print(f"Error sending log: {e}")

# Function triggered when a new member joins
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        chat_id = update.message.chat.id
        user_id = member.id
        user_name = member.first_name
        user_username = member.username  # Get the Telegram username (if available)

        # Add user to pending list with "not verified" status
        pending_users[user_id] = {
            "chat_id": chat_id,
            "verified": False,  # Not verified initially
            "timeout_task": None  # To store the timeout task reference
        }

        # Custom welcome message with Telegram username if available
        if user_username:
            welcome_text = f"欢迎 @{user_username} 👋、大家加入，想聊或着分享什么都可以，视频，旅游\n"
        else:
            welcome_text = f"欢迎 {user_name} 👋、大家加入，想聊或着分享什么都可以，视频，旅游\n"
        
        welcome_text += """
🔞只限男孩子

📌入群请先发张或自己的身材吊照！

📌不要刪，不要撤，方便管理员检查。

📌脸照一张！（管理员审核

﻿﻿📌自我介绍
﻿﻿称呼：
﻿﻿年龄：
﻿﻿地区：
﻿﻿高/重：
﻿﻿角色：
1号发屌照一张
0号发屁股照一张
（4小时无完成以会自动被退出群）
        """
        
        # Send the custom welcome message
        await context.bot.send_message(chat_id=chat_id, text=welcome_text)

        # Log this action
        await send_log(context, f"New member @{user_username if user_username else user_name} joined the group {chat_id}.")

        # Start a timer to kick the user if no photo is sent within 4 hours
        timeout_task = asyncio.create_task(timeout_user(user_id, context))  # Start a timeout task
        pending_users[user_id]["timeout_task"] = timeout_task

# Function to kick unverified users after timeout
async def timeout_user(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Waits for 4 hours and kicks unverified users."""
    await asyncio.sleep(4 * 60 * 60)  # Wait for 4 hours (4 hours * 60 minutes * 60 seconds)
    if user_id in pending_users and not pending_users[user_id]["verified"]:
        print(f"Timeout reached for user {user_id}, attempting to kick out.")
        await kick_unverified_user(context, user_id)

# Function to kick unverified users
async def kick_unverified_user(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Kicks users who don't send a photo within the time limit."""
    if user_id in pending_users:
        chat_id = pending_users[user_id]["chat_id"]
        try:
            # Retrieve the username of the user
            user_info = await context.bot.get_chat_member(chat_id, user_id)
            user_username = user_info.user.username if user_info.user.username else str(user_id)  # Use username if available, else fallback to user_id
            
            # Kick the user
            await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
            del pending_users[user_id]  # Remove from pending users list
            print(f"User {user_id} kicked out successfully.")
            
            # Send a message explaining why the user was removed
            kicked_message = await context.bot.send_message(
                chat_id=chat_id,
                text=f"@{user_username}，你因为未通过验证而被踢出群聊。"
            )
            
            # Log the action using the username if available
            await send_log(context, f"User @{user_username} was kicked out due to verification timeout.")
            
            # Delete the kicked out message after 15 seconds
            await asyncio.sleep(15)
            await context.bot.delete_message(chat_id=chat_id, message_id=kicked_message.message_id)
            print(f"Deleted kicked out message for User {user_id}")

        except Exception as e:
            print(f"Error kicking user {user_id}: {e}")

# Function to handle photos sent by users
async def verify_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifies users who send a photo."""
    user_id = update.message.from_user.id
    user_username = update.message.from_user.username  # Retrieve the user's Telegram username

    print(f"Received photo from user_id: {user_id}, username: {user_username}")

    if user_id in pending_users and not pending_users[user_id]["verified"]:
        print(f"User {user_id} is pending verification.")
        
        chat_id = pending_users[user_id]["chat_id"]
        
        # Mark the user as verified
        pending_users[user_id]["verified"] = True
        print(f"User {user_id} marked as verified.")
        
        # Cancel the timeout task
        timeout_task = pending_users[user_id].get("timeout_task")
        if timeout_task:
            timeout_task.cancel()
            print(f"Timeout task for user {user_id} cancelled.")

        # Remove the user from pending list
        del pending_users[user_id]

        # Send a success message
        try:
            if user_username:
                message = await context.bot.send_message(
                    chat_id=chat_id, 
                    text=f"@{user_username}，你已通过验证！"
                )
                print(f"Success message sent to @{user_username}")
            else:
                message = await context.bot.send_message(
                    chat_id=chat_id, 
                    text="你的验证已通过！"
                )
                print("Success message sent (no username).")
            
            # Log the verification
            await send_log(context, f"User @{user_username if user_username else user_id} has been verified successfully.")
            
            # Delete the success message after 10 seconds
            await asyncio.sleep(10)
            await context.bot.delete_message(chat_id=chat_id, message_id=message.message_id)
            print(f"Success message for user {user_id} deleted.")
        
        except Exception as e:
            print(f"Error sending verification message: {e}")

    else:
        print(f"User {user_id} not found in pending_users or already verified.")
        
# Main function
def main():
    # Build the application
    application = ApplicationBuilder().token("8027056676:AAEXbDxW3qO0l66DAlbQvIge9mpPxqNBiFw").build()

    # Add Handlers
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    application.add_handler(MessageHandler(filters.PHOTO, verify_photo))

    # Start the bot
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()