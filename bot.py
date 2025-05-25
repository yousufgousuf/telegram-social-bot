import os import logging from telegram import Update, Bot from telegram.ext import ( ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, ConversationHandler, filters ) from dotenv import load_dotenv

إعداد تسجيل الأخطاء

logging.basicConfig( format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO ) logger = logging.getLogger(name)

تحميل متغيرات البيئة

load_dotenv() TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") TELEGRAM_CHANNEL = os.getenv("TELEGRAM_CHANNEL")

تعريف الحالات

TEXT, MEDIA, CONFIRM = range(3)

بدء المحادثة

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: await update.message.reply_text("مرحباً بك!\nأرسل لي نصّ المنشور أولاً.") return TEXT

استلام النص

async def get_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: context.user_data['text'] = update.message.text await update.message.reply_text("رائع!\nالآن أرسل صورة أو فيديو (اختياري)، أو أرسل كلمة 'تخطي'.") return MEDIA

استلام الوسائط

async def get_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: msg = update.message media = None media_type = None if msg.photo: media = msg.photo[-1] media_type = 'photo' elif msg.video: media = msg.video media_type = 'video'

if media:
    file = await context.bot.get_file(media.file_id)
    os.makedirs("downloads", exist_ok=True)
    path = f"downloads/{media.file_id}"
    await file.download_to_drive(path)
    context.user_data['media'] = path
    context.user_data['media_type'] = media_type

return await confirm_post(update, context)

تخطي الوسائط

async def skip_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: return await confirm_post(update, context)

تأكيد النشر

async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: text = context.user_data.get("text") await update.message.reply_text( f"جيد!\nهذا نصّ المنشور:\n\n{text}\n\n" "أرسل الآن الكلمة (كل) للنشر في جميع المنصات، أو (تيليجرام) للنشر في تيليجرام فقط." ) return CONFIRM

تنفيذ النشر

async def publish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: platform = update.message.text.strip().lower() text = context.user_data.get("text") media = context.user_data.get("media") media_type = context.user_data.get("media_type")

if platform in ["كل", "تيليجرام"]:
    bot = Bot(TELEGRAM_TOKEN)
    if media:
        with open(media, "rb") as f:
            if media_type == 'photo':
                await bot.send_photo(chat_id=TELEGRAM_CHANNEL, photo=f, caption=text)
            else:
                await bot.send_video(chat_id=TELEGRAM_CHANNEL, video=f, caption=text)
    else:
        await bot.send_message(chat_id=TELEGRAM_CHANNEL, text=text)

    await update.message.reply_text("✅ تم النشر بنجاح!")
else:
    await update.message.reply_text("⚠️ لم أفهم المنصة. أرسل (كل) أو (تيليجرام).")
    return CONFIRM

return ConversationHandler.END

إلغاء المحادثة

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int: await update.message.reply_text("تم إلغاء العملية.") return ConversationHandler.END

if name == "main": app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_text)],
        MEDIA: [
            MessageHandler(filters.PHOTO | filters.VIDEO, get_media),
            MessageHandler(filters.TEXT & filters.Regex("^(تخطي)$"), skip_media)
        ],
        CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, publish)]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

app.add_handler(conv_handler)
print("🤖 Bot is now polling for updates...")
app.run_polling()

