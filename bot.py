import os
import requests
import tweepy
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# تحميل متغيرات البيئة من .env
load_dotenv()

# متغيّرات البيئة
TELEGRAM_TOKEN    = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHANNEL  = os.getenv("TELEGRAM_CHANNEL")
TW_CONSUMER_KEY        = os.getenv("TW_CONSUMER_KEY")
TW_CONSUMER_SECRET     = os.getenv("TW_CONSUMER_SECRET")
TW_ACCESS_TOKEN        = os.getenv("TW_ACCESS_TOKEN")
TW_ACCESS_TOKEN_SECRET = os.getenv("TW_ACCESS_TOKEN_SECRET")
FACEBOOK_TOKEN      = os.getenv("FACEBOOK_TOKEN")
FACEBOOK_PAGE_ID    = os.getenv("FACEBOOK_PAGE_ID")

# إعداد Tweepy
auth = tweepy.OAuth1UserHandler(
    TW_CONSUMER_KEY, TW_CONSUMER_SECRET,
    TW_ACCESS_TOKEN, TW_ACCESS_TOKEN_SECRET
)
twitter_api = tweepy.API(auth, wait_on_rate_limit=True)

def post_to_twitter(text, media_path=None):
    if media_path:
        media = twitter_api.media_upload(media_path)
        twitter_api.update_status(status=text, media_ids=[media.media_id])
    else:
        twitter_api.update_status(status=text)

def post_to_facebook(text, media_path=None, is_video=False):
    page = FACEBOOK_PAGE_ID
    if media_path:
        endpoint = "photos" if not is_video else "videos"
        url = f"https://graph.facebook.com/{page}/{endpoint}"
        files = {"source": open(media_path, "rb")}
        data = {
            "caption" if not is_video else "description": text,
            "access_token": FACEBOOK_TOKEN
        }
        requests.post(url, data=data, files=files)
    else:
        url = f"https://graph.facebook.com/{page}/feed"
        requests.post(url, data={"message": text, "access_token": FACEBOOK_TOKEN})

# /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "مرحباً!\n"
        "أرسل لي نصّ المنشور مع صورة/فيديو (اختياري)، سأعرض لك ثمّ أرسل على المنصات."
    )

# handle incoming photo or video
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    media = msg.photo[-1] if msg.photo else msg.video
    file = await context.bot.get_file(media.file_id)
    os.makedirs("downloads", exist_ok=True)
    path = f"downloads/{media.file_id}"
    await file.download_to_drive(path)

    context.user_data["payload"] = {
        "text": msg.caption or "",
        "media": path,
        "is_video": bool(msg.video),
        "platforms": set()
    }

    keyboard = [
        [
            InlineKeyboardButton("Twitter", callback_data="TW"),
            InlineKeyboardButton("Facebook", callback_data="FB"),
            InlineKeyboardButton("Telegram", callback_data="TG"),
        ],
        [InlineKeyboardButton("إرسال على الكل ✅", callback_data="ALL")],
    ]
    await msg.reply_text("اختر المنصات للنشر:", reply_markup=InlineKeyboardMarkup(keyboard))

# button press handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    payload = context.user_data.get("payload")
    if not payload:
        return await query.edit_message_text("أرسل صورة أو فيديو أولاً.")

    if data in {"TW", "FB", "TG"}:
        payload["platforms"].add(data)
        chosen = ", ".join(payload["platforms"])
        return await query.edit_message_text(f"✓ اخترت: {chosen}\nاضغط إرسال للكل.")

    # ALL
    text = payload["text"]
    media = payload["media"]
    is_vid = payload["is_video"]
    plats = payload["platforms"] or {"TW", "FB", "TG"}

    if "TW" in plats:
        post_to_twitter(text, media)
    if "FB" in plats:
        post_to_facebook(text, media, is_vid)
    if "TG" in plats:
        bot = Bot(TELEGRAM_TOKEN)
        if is_vid:
            await bot.send_video(chat_id=TELEGRAM_CHANNEL, video=open(media, "rb"), caption=text)
        else:
            await bot.send_photo(chat_id=TELEGRAM_CHANNEL, photo=open(media, "rb"), caption=text)

    await query.edit_message_text("🚀 تم النشر على: " + ", ".join(plats))
    context.user_data.clear()

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Bot is now polling for updates...")
    app.run_polling()
