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

BOT_TOKEN = "8520547535:AAHeirjxbLZ3GiQqA_ksKIvoJ-RmxZtuA0w"

# Картинка должна быть <= 10MB и реально называться как в коде.
# У тебя было welcome.jpg.jpg — лучше переименуй в welcome.jpg
WELCOME_IMAGE_PATH = "welcome.jpg"

WELCOME_TEXT = (
    "👑 PRIVATE ARENA\n\n"
    "Закрытый турнир по Clash Royale.\n\n"
    "📅 28.02\n"
    "🎮 Формат: 1v1\n"
    "🔒 Доступ после оплаты"
)

ADMIN_IDS = [1195876661, 5083187149]  # ваши user_id (админы)

PRICE_STARS = 100  # сколько звёзд

def keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ Вход за 100 звёзд", callback_data="buy_fake")],
        [InlineKeyboardButton("❓ Тех.поддержка", callback_data="support_start")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Каждый раз /start будет заново слать картинку+текст+кнопки
    with open(WELCOME_IMAGE_PATH, "rb") as f:
        await update.message.reply_photo(
            photo=f,
            caption=WELCOME_TEXT,
            reply_markup=keyboard()
        )

# ========== ПОКУПКА ЗВЁЗДАМИ ==========
async def on_buy_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    # Инвойс (Stars)
    # currency="XTR", provider_token="" и prices = ровно 1 пункт. :contentReference[oaicite:1]{index=1}
    prices = [LabeledPrice(label="Доступ к турниру", amount=PRICE_STARS)]

    await q.message.reply_invoice(
        title="Доступ к турниру",
        description="Оплата 100 звёзд за доступ.",
        payload="access_100_stars",      # любая строка для твоей логики
        provider_token="",              # для Stars пусто :contentReference[oaicite:2]{index=2}
        currency="XTR",                 # Telegram Stars :contentReference[oaicite:3]{index=3}
        prices=prices,                  # 1 пункт :contentReference[oaicite:4]{index=4}
    )

async def precheckout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Без этого оплата не пройдёт
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sp = update.message.successful_payment
    # тут ты “выдаёшь доступ”
    context.user_data["paid_access"] = True

    await update.message.reply_text("✅ Оплата прошла! Доступ выдан.")

    # (опционально) уведомить админов
    user = update.effective_user
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

# ========== ТЕХПОДДЕРЖКА (ваш текущий флоу) ==========
async def on_support_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["waiting_support_message"] = True
    await q.message.reply_text("🛟 Напиши сюда одним сообщением, что нужно. Я отправлю админам.")

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

    app.add_handler(CallbackQueryHandler(on_buy_stars, pattern="^buy_stars$"))
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    app.add_handler(CallbackQueryHandler(on_support_start, pattern="^support_start$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_user_text))

    app.run_polling()

if __name__ == "__main__":
    main()