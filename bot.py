# bot.py
import os
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
)

# ===== ENV =====
BOT_TOKEN = os.getenv("8520547535:AAHeirjxbLZ3GiQqA_ksKIvoJ-RmxZtuA0w")  # Railway Variables -> BOT_TOKEN
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set. Add it in Railway -> Variables.")

# ===== FILES =====
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WELCOME_IMAGE_PATH = os.path.join(BASE_DIR, "welcome.jpg")

# ===== TEXT / SETTINGS =====
WELCOME_TEXT = (
    "👑 PRIVATE ARENA\n\n"
    "Закрытый турнир по Clash Royale.\n\n"
    "📅 28.02\n"
    "🎮 Формат: 1v1\n"
    "🔒 Доступ после оплаты"
)

ADMIN_IDS = [1195876661, 5083187149]   # твои админы (user_id)
PRICE_STARS = 100                      # сколько звёзд

# ===== UI =====
def keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Вход за 100 звёзд", callback_data="buy_stars")],
        [InlineKeyboardButton("❓ Тех.поддержка", callback_data="support_start")],
    ])

# ===== COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /start всегда шлёт картинку+текст+кнопки
    if update.message is None:
        return

    if not os.path.exists(WELCOME_IMAGE_PATH):
        await update.message.reply_text(
            "⚠️ Не нашёл welcome.jpg в корне проекта.\n"
            "Проверь название файла и что он задеплоен."
        )
        return

    with open(WELCOME_IMAGE_PATH, "rb") as f:
        await update.message.reply_photo(
            photo=f,
            caption=WELCOME_TEXT,
            reply_markup=keyboard()
        )

# ===== STARS PAYMENT =====
async def on_buy_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()

    # Важно:
    # - currency="XTR"
    # - provider_token="" (пусто для Stars)
    # - prices: ровно 1 пункт
    prices = [LabeledPrice(label="Доступ к турниру", amount=PRICE_STARS)]

    await q.message.reply_invoice(
        title="Доступ к турниру",
        description="Оплата 100 звёзд за доступ.",
        payload="access_100_stars",
        provider_token="",
        currency="XTR",
        prices=prices,
    )

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Без этого платеж не завершится
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Успешная оплата
    context.user_data["paid_access"] = True

    user = update.effective_user
    sp = update.message.successful_payment

    await update.message.reply_text("✅ Оплата прошла! Доступ выдан.")

    # Нотификация админам
    admin_text = (
        "💸 NEW PAYMENT\n"
        f"👤 {user.full_name}\n"
        f"🆔 {user.id}\n"
        f"@{user.username if user.username else 'no_username'}\n"
        f"⭐ amount: {sp.total_amount} {sp.currency}\n"
        f"payload: {sp.invoice_payload}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=admin_text)
        except Exception as e:
            print(f"Can't send to admin {admin_id}: {e}")

# ===== SUPPORT FLOW =====
async def on_support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q:
        return
    await q.answer()

    context.user_data["waiting_support_message"] = True
    await q.message.reply_text("✉️ Напишите ваш вопрос в одном сообщении:git add bot.py")

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

# ===== RUN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(CallbackQueryHandler(on_buy_stars, pattern="^buy_stars$"))
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    app.add_handler(CallbackQueryHandler(on_support_start, pattern="^support_start$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_user_text))

    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()