import os import logging import asyncio import requests import tweepy from dotenv import load_dotenv from telegram import ( InlineKeyboardButton, InlineKeyboardMarkup, Update, Bot, InputMediaPhoto, InputMediaVideo ) from telegram.ext import ( ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters )

----------------------

Configuration & Setup

----------------------

Load environment variables

load_dotenv()

Telegram

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL")  # e.g. @channel_username

Twitter

TW_CONSUMER_KEY = os.getenv("TW_CONSUMER_KEY") TW_CONSUMER_SECRET = os.getenv("TW_CONSUMER_SECRET") TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN") TW_ACCESS_TOKEN_SECRET = os.getenv("TW_ACCESS_TOKEN_SECRET")

Facebook

FACEBOOK_TOKEN = os.getenv("FACEBOOK_TOKEN") FACEBOOK_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")

Logging

logging.basicConfig( format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO ) logger = logging.getLogger(name)

Initialize Twitter API

twitter_auth = tweepy.OAuth1UserHandler( TW_CONSUMER_KEY, TW_CONSUMER_SECRET, TW_ACCESS_TOKEN, TW_ACCESS_TOKEN_SECRET ) twitter_api = tweepy.API(twitter_auth, wait_on_rate_limit=True)

--------------

Helper Methods

--------------

def make_keyboard(selected: set): """ Build dynamic inline keyboard with selected platforms marked. """ buttons = [] for code, label in [('TW', 'Twitter'), ('FB', 'Facebook'), ('TG', 'Telegram')]: prefix = '✓ ' if code in selected else '' buttons.append(InlineKeyboardButton(prefix + label, callback_data=code))

keyboard = [buttons, [InlineKeyboardButton('📤 نشر على جميع المنصات', callback_data='ALL')]]
return InlineKeyboardMarkup(keyboard)

async def post_to_twitter(text: str, media_path=None): """Post text (and optional media) to Twitter.""" try: if media_path: media = twitter_api.media_upload(media_path) twitter_api.update_status(status=text, media_ids=[media.media_id]) else: twitter_api.update_status(status=text) logger.info("Posted to Twitter") except Exception as e: logger.error(f"Twitter post failed: {e}")

async def post_to_facebook(text: str, media_path=None, is_video=False): """Post text (and optional media) to Facebook Page.""" try: page = FACEBOOK_PAGE_ID if media_path: endpoint = 'photos' if not is_video else 'videos' url = f"https://graph.facebook.com/{page}/{endpoint}" with open(media_path, 'rb') as f: files = {'source': f} data = {'access_token': FACEBOOK_TOKEN} if is_video: data['description'] = text else: data['caption'] = text requests.post(url, data=data, files=files) else: url = f"https://graph.facebook.com/{page}/feed" requests.post(url, data={'message': text, 'access_token': FACEBOOK_TOKEN}) logger.info("Posted to Facebook") except Exception as e: logger.error(f"Facebook post failed: {e}")

async def post_to_telegram(text: str, media_path=None, is_video=False): """Post to Telegram channel.""" bot = Bot(TELEGRAM_TOKEN) try: if media_path: if is_video: await bot.send_video(chat_id=TELEGRAM_CHANNEL, video=open(media_path, 'rb'), caption=text) else: await bot.send_photo(chat_id=TELEGRAM_CHANNEL, photo=open(media_path, 'rb'), caption=text) else: await bot.send_message(chat_id=TELEGRAM_CHANNEL, text=text) logger.info("Posted to Telegram Channel") except Exception as e: logger.error(f"Telegram post failed: {e}")

--------------

Command Handlers

--------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE): """ Handle /start command. """ text = ( "مرحباً! 👋\n" "أنا بوت اجتماعي قوي، يمكنني نشر رسائلك وصورك وفيديوهاتك على Telegram، Twitter، وFacebook بسهولة.\n" "للبدء، أرسل نصًا أو نصًا مع صورة/فيديو.") await update.message.reply_text(text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE): """Handle /help command.""" text = ( "استخدام البوت:\n" "1. أرسل نصًا (اختياريًا مع صورة/فيديو).\n" "2. اختر المنصات عبر الأزرار.\n" "3. اضغط '📤 نشر على جميع المنصات' للتأكيد.\n" "\nالأوامر:\n" "/start - بدء المحادثة.\n" "/help - عرض التعليمات.") await update.message.reply_text(text)

--------------

Message Handlers

--------------

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE): """ Handle plain text messages. """ payload = { 'text': update.message.text, 'media': None, 'is_video': False, 'platforms': set() } context.user_data['payload'] = payload await update.message.reply_text( '🔔 اختر المنصات للنشر:', reply_markup=make_keyboard(set()) )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE): """ Handle photo or video messages. """ msg = update.message media = msg.photo[-1] if msg.photo else msg.video file = await context.bot.get_file(media.file_id) os.makedirs('downloads', exist_ok=True) path = f"downloads/{media.file_id}" await file.download_to_drive(path)

payload = {
    'text': msg.caption or '',
    'media': path,
    'is_video': bool(msg.video),
    'platforms': set()
}
context.user_data['payload'] = payload
await msg.reply_text(
    '🔔 اختر المنصات للنشر:',
    reply_markup=make_keyboard(set())
)

-----------------

Callback Handler

-----------------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() data = query.data payload = context.user_data.get('payload') if not payload: return await query.edit_message_text('⚠️ لم أجد محتوى للنشر، أرسل نصًا أو صورة/فيديو أولاً.')

# Toggle platform selection
if data in {'TW', 'FB', 'TG'}:
    if data in payload['platforms']:
        payload['platforms'].remove(data)
    else:
        payload['platforms'].add(data)
    await query.edit_message_text(
        f"✅ تم اختيار: {', '.join(payload['platforms']) or 'لا شيء'}\nاضغط 📤 للنشر.",
        reply_markup=make_keyboard(payload['platforms'])
    )
    return

# Post to all selected platforms
if data == 'ALL':
    platforms = payload['platforms'] or {'TW', 'FB', 'TG'}
    text = payload['text']
    media = payload['media']
    is_vid = payload['is_video']

    # Run posts concurrently
    tasks = []
    if 'TW' in platforms:
        tasks.append(post_to_twitter(text, media))
    if 'FB' in platforms:
        tasks.append(post_to_facebook(text, media, is_vid))
    if 'TG' in platforms:
        tasks.append(post_to_telegram(text, media, is_vid))

    await asyncio.gather(*tasks)
    context.user_data.clear()
    await query.edit_message_text(
        f"🚀 تم النشر بنجاح على: {', '.join(platforms)}"
    )

--------

Main

--------

if name == 'main': app = ApplicationBuilder().token(TELEGRAM_TOKEN).build() # Commands app.add_handler(CommandHandler('start', start)) app.add_handler(CommandHandler('help', help_command)) # Messages app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media)) app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)) # Callbacks app.add_handler(CallbackQueryHandler(button_handler))

logger.info('🤖 Bot is polling for updates...')
app.run_polling()

