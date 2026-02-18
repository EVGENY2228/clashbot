import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ===== ENV =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Add it in Railway -> Variables.")

# ===== SETTINGS =====
ADMIN_IDS = [1195876661, 5083187149]   # твои админы
TOURNAMENT_INFO = "✅ Доступ выдан.\nПароль/инфа: (вставь сюда)\n"
CHANNEL_LINK = ""  # можно вставить инвайт-ссылку, если хочешь: https://t.me/+xxxx

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WELCOME_IMAGE_PATH = os.path.join(BASE_DIR, "welcome.jpg")

WELCOME_TEXT = (
    "👑 PRIVATE ARENA\n\n"
    "Закрытый турнир по Clash Royale.\n\n"
    "📅 28.02\n"
    "🎮 Формат: 1v1\n"
    "🔒 Доступ после оплаты\n\n"
    "💳 Оплата через Bit: пришли скрин перевода."
)

# ===== UI =====
def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 Оплатил через Bit (скинуть скрин)", callback_data="bit_start")],
        [InlineKeyboardButton("❓ Тех.поддержка", callback_data="support_start")],
    ])

def admin_review_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"bit_approve:{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"bit_reject:{user_id}"),
        ]
    ])

# ===== COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    if os.path.exists(WELCOME_IMAGE_PATH):
        with open(WELCOME_IMAGE_PATH, "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption=WELCOME_TEXT,
                reply_markup=main_keyboard()
            )
    else:
        await update.message.reply_text(WELCOME_TEXT, reply_markup=main_keyboard())

# ===== BIT FLOW =====
async def bit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()

    context.user_data["waiting_bit_screenshot"] = True
    await q.message.reply_text(
        "🎟 Участие в турнире — 10 ₪\n\n"
        "1️⃣ Переведи 10 ₪ через Bit\n"
        "2️⃣ В комментарии к переводу укажи свой Telegram @username\n"
        "3️⃣ Пришли сюда скрин одним фото\n\n"
        "После проверки откроем доступ.\n\n"
        "⏳ Платёж на проверке.\n"
        "Обычно до 10–15 минут."
    )

async def on_user_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ждём скрин именно после нажатия кнопки
    if not context.user_data.get("waiting_bit_screenshot"):
        return

    context.user_data["waiting_bit_screenshot"] = False

    user = update.effective_user
    chat_id = update.effective_chat.id

    # берём самое большое фото
    photo = update.message.photo[-1]
    caption = (
        "💳 BIT PAYMENT CHECK\n"
        f"👤 {user.full_name}\n"
        f"🆔 user_id: {user.id}\n"
        f"chat_id: {chat_id}\n"
        f"@{user.username if user.username else 'no_username'}\n\n"
        "Нажми Approve/Reject:"
    )

    await update.message.reply_text("✅ Скрин получил. Отправил админам на проверку.")

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=photo.file_id,
                caption=caption,
                reply_markup=admin_review_keyboard(user.id)
            )
        except Exception as e:
            print(f"Can't send to admin {admin_id}: {e}")

async def bit_admin_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return

    admin_id = q.from_user.id
    if admin_id not in ADMIN_IDS:
        await q.answer("Not allowed", show_alert=True)
        return

    await q.answer()

    data = q.data  # bit_approve:<user_id> или bit_reject:<user_id>
    action, user_id_str = data.split(":")
    user_id = int(user_id_str)

    if action == "bit_approve":
        # пометим в памяти
        context.application.bot_data.setdefault("approved_users", set()).add(user_id)

        # уведомим юзера
        msg = TOURNAMENT_INFO
        if CHANNEL_LINK:
            msg += f"\n🔗 Ссылка: {CHANNEL_LINK}"

        try:
            await context.bot.send_message(chat_id=user_id, text=msg)
        except Exception as e:
            print("Can't message user:", e)

        await q.edit_message_caption(
            caption=(q.message.caption or "") + "\n\n✅ APPROVED",
            reply_markup=None
        )

    elif action == "bit_reject":
        try:
            await update.message.reply_text(
                "❌ Платёж не удалось подтвердить.\n\n"
                "Проверь, пожалуйста, скрин:\n"
                "— видно ли сумму 10 ₪\n"
                "— виден ли комментарий с твоим @username\n\n"
                "Пришли фото ещё раз или напиши в поддержку."
            )git add .
        except Exception as e:
            print("Can't message user:", e)

        await q.edit_message_caption(
            caption=(q.message.caption or "") + "\n\n❌ REJECTED",
            reply_markup=None
        )

# ===== SUPPORT FLOW (твой простой вариант) =====
async def on_support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()
    context.user_data["waiting_support_message"] = True
    await q.message.reply_text("🛟 Напиши одним сообщением, что нужно. Я отправлю админам.")

async def on_user_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_support_message"):
        return

    context.user_data["waiting_support_message"] = False

    user = update.effective_user
    text = update.message.text

    await update.message.reply_text("✅ Принято. Мы скоро ответим.")

    admin_text = (
        "🆘 SUPPORT MESSAGE\n"
        f"👤 {user.full_name}\n"
        f"🆔 id: {user.id}\n"
        f"@{user.username if user.username else 'no_username'}\n\n"
        f"💬 {text}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=admin_text)
        except Exception as e:
            print(f"Can't send to admin {admin_id}: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # bit flow
    app.add_handler(CallbackQueryHandler(bit_start, pattern="^bit_start$"))
    app.add_handler(MessageHandler(filters.PHOTO, on_user_photo))
    app.add_handler(CallbackQueryHandler(bit_admin_decision, pattern="^bit_(approve|reject):"))

    # support
    app.add_handler(CallbackQueryHandler(on_support_start, pattern="^support_start$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_user_text))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()