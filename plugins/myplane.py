import os
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from helper.database import find_one, used_limit, daily as daily_, uploadlimit, usertype
from helper.progress import humanbytes
from helper.date import check_expi
from datetime import datetime, date

# Define environment variables for sensitive information
API_ID = int(os.environ.get("API_ID", ""))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

app = Client("my_bot", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

@app.on_message(filters.private & filters.command(["myplan"]))
async def start(client, message):
    user_id = message.from_user.id
    user_data = find_one(user_id)
    daily_limit = user_data["daily"]
    current_date = date.today()
    epoch_today = int(time.mktime(time.strptime(str(current_date), '%Y-%m-%d')))

    # Check if the daily limit needs to be reset
    if daily_limit != epoch_today:
        daily_(user_id, epoch_today)
        used_limit(user_id, 0)

    # Retrieve updated user data
    updated_user_data = find_one(user_id)
    used = updated_user_data["used_limit"]
    limit = updated_user_data["uploadlimit"]
    remaining = limit - used
    user_type = updated_user_data["usertype"]
    expiration_date = updated_user_data["prexdate"]

    if expiration_date:
        if not check_expi(expiration_date):
            uploadlimit(user_id, 1288490188)
            usertype(user_id, "Free")
    
    # Generate the response text
    if expiration_date is None:
        text = (f"User ID:- ```{user_id}```\nPlan :- {user_type}\nDaily Upload Limit :- {humanbytes(limit)}\n"
                f"Today Used :- {humanbytes(used)}\nRemain:- {humanbytes(remaining)}")
    else:
        formatted_date = datetime.fromtimestamp(expiration_date).strftime('%Y-%m-%d')
        text = (f"User ID:- ```{user_id}```\nPlan :- {user_type}\nDaily Upload Limit :- {humanbytes(limit)}\n"
                f"Today Used :- {humanbytes(used)}\nRemain:- {humanbytes(remaining)}\n\nYour Plan Ends On :- {formatted_date}")

    # Send the reply with an inline keyboard if the user is on a free plan
    if user_type == "Free":
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("Upgrade 💰💳", callback_data="upgrade"),
             InlineKeyboardButton("Cancel ✖️", callback_data="cancel")]
        ])
        await message.reply(text, quote=True, reply_markup=reply_markup)
    else:
        await message.reply(text, quote=True)

app.run()
