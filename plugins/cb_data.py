from helper.progress import progress_for_pyrogram, TimeFormatter
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply
from hachoir.metadata import extractMetadata
from hachoir.parser import createParser
from helper.database import *
import os
import random
from PIL import Image
import time
from datetime import timedelta
from helper.ffmpeg import take_screen_shot, fix_thumb
from helper.progress import humanbytes
from helper.set import escape_invalid_curly_brackets

log_channel = int(os.environ.get("LOG_CHANNEL", ""))
API_ID = int(os.environ.get("API_ID", ""))
API_HASH = os.environ.get("API_HASH", "")
STRING = os.environ.get("STRING", "")
ADMIN = os.environ.get("ADMIN", "")

app = Client("test", api_id=API_ID, api_hash=API_HASH, session_string=STRING)

def sanitize_path(base_dir, path):
    """Ensure the file path is within the allowed directory."""
    full_path = os.path.join(base_dir, os.path.basename(path))
    if not os.path.abspath(full_path).startswith(os.path.abspath(base_dir)):
        raise ValueError("Invalid file path")
    return full_path

async def handle_file_download_and_upload(update, file_type):
    """Download, process, and upload files based on type."""
    new_name = update.message.text
    user_id = update.from_user.id
    used_ = find_one(user_id)
    used = used_["used_limit"]
    date = used_["date"]
    name = new_name.split(":-")
    new_filename = name[1]
    file_path = sanitize_path("downloads", new_filename)
    message = update.message.reply_to_message
    file = message.document or message.video or message.audio

    ms = await update.message.edit("```Trying To Download...```")
    used_limit(user_id, file.file_size)
    c_time = time.time()
    total_used = used + int(file.file_size)
    used_limit(user_id, total_used)
    
    try:
        path = await bot.download_media(message=file, progress=progress_for_pyrogram, progress_args=("``` Trying To Download...```", ms, c_time))
    except Exception as e:
        neg_used = used - int(file.file_size)
        used_limit(user_id, neg_used)
        await ms.edit(f"Error: {e}")
        return

    splitpath = path.split("/downloads/")
    dow_file_name = splitpath[1]
    old_file_name = f"downloads/{dow_file_name}"
    os.rename(old_file_name, file_path)

    data = find(update.message.chat.id)
    thumb = data[0]
    c_caption = data.get(1, None)

    if file_type == 'doc':
        caption = c_caption.format(filename=new_filename, filesize=humanbytes(file.file_size)) if c_caption else f"**{new_filename}**"
    elif file_type == 'vid':
        duration = 0
        metadata = extractMetadata(createParser(file_path))
        if metadata.has("duration"):
            duration = metadata.get('duration').seconds
        caption = c_caption.format(filename=new_filename, filesize=humanbytes(file.file_size), duration=timedelta(seconds=duration)) if c_caption else f"**{new_filename}**"
    elif file_type == 'aud':
        duration = 0
        metadata = extractMetadata(createParser(file_path))
        if metadata.has("duration"):
            duration = metadata.get('duration').seconds
        caption = c_caption.format(filename=new_filename, filesize=humanbytes(file.file_size), duration=timedelta(seconds=duration)) if c_caption else f"**{new_filename}**"

    if thumb:
        try:
            ph_path = await bot.download_media(thumb)
            Image.open(ph_path).convert("RGB").save(ph_path)
            img = Image.open(ph_path)
            img.resize((320, 320)).save(ph_path, "JPEG")
        except Exception as e:
            ph_path = None
            print(e)
    else:
        ph_path = None
        if file_type == 'vid':
            try:
                duration = metadata.get('duration').seconds
                ph_path_ = await take_screen_shot(file_path, os.path.dirname(os.path.abspath(file_path)), random.randint(0, duration - 1))
                width, height, ph_path = await fix_thumb(ph_path_)
            except Exception as e:
                print(e)
                ph_path = None

    await ms.edit("```Trying To Upload```")
    try:
        if file.file_size > 2090000000:
            if file_type == 'doc':
                filw = await app.send_document(log_channel, document=file_path, thumb=ph_path, caption=caption, progress=progress_for_pyrogram, progress_args=("```Trying To Uploading```", ms, c_time))
            elif file_type == 'vid':
                filw = await app.send_video(log_channel, video=file_path, thumb=ph_path, duration=duration, caption=caption, progress=progress_for_pyrogram, progress_args=("```Trying To Uploading```", ms, c_time))
            elif file_type == 'aud':
                filw = await bot.send_audio(log_channel, audio=file_path, caption=caption, thumb=ph_path, duration=duration, progress=progress_for_pyrogram, progress_args=("```Trying To Uploading```", ms, c_time))
            from_chat = filw.chat.id
            mg_id = filw.id
            time.sleep(2)
            await bot.copy_message(update.from_user.id, from_chat, mg_id)
        else:
            if file_type == 'doc':
                await bot.send_document(update.from_user.id, document=file_path, thumb=ph_path, caption=caption, progress=progress_for_pyrogram, progress_args=("```Trying To Uploading```", ms, c_time))
            elif file_type == 'vid':
                await bot.send_video(update.from_user.id, video=file_path, thumb=ph_path, duration=duration, caption=caption, progress=progress_for_pyrogram, progress_args=("```Trying To Uploading```", ms, c_time))
            elif file_type == 'aud':
                await bot.send_audio(update.from_user.id, audio=file_path, caption=caption, duration=duration, progress=progress_for_pyrogram, progress_args=("```Trying To Uploading```", ms, c_time))

        await ms.delete()
    except Exception as e:
        neg_used = used - int(file.file_size)
        used_limit(user_id, neg_used)
        await ms.edit(f"Error: {e}")
    finally:
        os.remove(file_path)
        if ph_path:
            try:
                os.remove(ph_path)
            except:
                pass

@Client.on_callback_query(filters.regex('cancel'))
async def cancel(bot, update):
    try:
        await update.message.delete()
    except Exception as e:
        print(f"Error in cancel: {e}")

@Client.on_callback_query(filters.regex('rename'))
async def rename(bot, update):
    date_fa = str(update.message.date)
    pattern = '%Y-%m-%d %H:%M:%S'
    date = int(time.mktime(time.strptime(date_fa, pattern)))
    chat_id = update.message.chat.id
    id = update.message.reply_to_message_id
    await update.message.delete()
    await update.message.reply_text(f"__Please enter the new filename...__\n\nNote:- Extension Not Required", reply_to_message_id=id, reply_markup=ForceReply(True))
    dateupdate(chat_id, date)

@Client.on_callback_query(filters.regex("doc"))
async def doc(bot, update):
    await handle_file_download_and_upload(update, 'doc')

@Client.on_callback_query(filters.regex("vid"))
async def vid(bot, update):
    await handle_file_download_and_upload(update, 'vid')

@Client.on_callback_query(filters.regex("aud"))
async def aud(bot, update):
    await handle_file_download_and_upload(update, 'aud')
