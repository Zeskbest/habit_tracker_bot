import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters, MessageHandler,
)

from db import get_all_series, update_series, log_increment, delete_series, add_series, init_db
from plot import generate_graph


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /menu to access the series menu.")


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    series_names = get_all_series(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"choose_{name}")] for name in series_names
    ]
    keyboard.append([InlineKeyboardButton("Create Series", callback_data="create")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query is not None:
        await update.callback_query.edit_message_text("Select a series or create a new one:", reply_markup=reply_markup)
    else:
        await update.effective_chat.send_message("Select a series or create a new one:", reply_markup=reply_markup)


async def handle_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Series menu"""
    query = update.callback_query
    await query.answer()

    series_name = context.user_data["current_series"]
    series_keyboard = [
        [
            InlineKeyboardButton("Increase", callback_data="increase"),
            InlineKeyboardButton("Apply", callback_data="apply"),
            InlineKeyboardButton("Cancel", callback_data="cancel")
        ],
        [InlineKeyboardButton("Graph", callback_data="graph_menu")],
        [InlineKeyboardButton("Remove Series", callback_data="remove")],
        [InlineKeyboardButton("Back to Menu", callback_data="menu")],
    ]
    series_reply_markup = InlineKeyboardMarkup(series_keyboard)

    data = query.data
    if data.startswith("choose_"):
        await query.edit_message_text(f"Selected series: {series_name}", reply_markup=series_reply_markup)
    elif data == "graph_menu":
        await graph_menu(update, context)  # Show graph menu
    elif data.startswith("graph_"):
        period = data.split("_", 1)[1]  # e.g., "graph_weekday" -> "weekday"
        graph_bytes = generate_graph(series_name, update.effective_user.id, period)
        if graph_bytes:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=graph_bytes)
        else:
            await query.edit_message_text(f"No data for '{series_name}' in the selected period.")
    elif data == "increase":
        context.user_data["increment"] = context.user_data.get("increment", 0) + 1
        await query.edit_message_text(
            f"Selected series: {series_name}. Unsaved counter: {context.user_data['increment']}.",
            reply_markup=series_reply_markup
        )
    elif data == "apply":
        increment = context.user_data.pop("increment", 0)
        if series_name and increment:
            count = update_series(series_name, update.effective_user.id, increment)
            log_increment(series_name, update.effective_user.id)
            await query.edit_message_text(f"Selected series: {series_name}. Applied {increment}. Total: {count}",
                                          reply_markup=series_reply_markup)
        else:
            await query.edit_message_text(f"Selected series: {series_name}. Not changed.",
                                          reply_markup=series_reply_markup)
    elif data == "cancel":
        context.user_data.pop("increment", None)
        await query.edit_message_text(f"Selected series: {series_name}. Changes canceled.",
                                      reply_markup=series_reply_markup)
    elif data == "remove":
        if series_name:
            delete_series(series_name, update.effective_user.id)
            await query.edit_message_text(f"Series '{series_name}' removed.", )
        else:
            await query.edit_message_text("No series selected.")
    elif data == "menu":
        context.user_data.pop("current_series")
        await handle_menu(update, context)
    else:
        raise RuntimeError(f"Unsupported data: {data}")


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main menu"""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "create":
        await query.edit_message_text("Send the name of the new series.")
        context.user_data["awaiting_series_name"] = True
    elif data.startswith("choose_"):
        series_name = data.split("_", 1)[1]
        context.user_data["current_series"] = series_name
        await handle_series(update, context)
    elif data in ("menu", "increase", "cancel", "remove", "apply") or data.startswith("graph_"):
        await menu(update, context)
    else:
        raise RuntimeError(f"Unsupported data: {data}")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "current_series" in context.user_data:
        await handle_series(update, context)
    else:
        await handle_menu(update, context)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("awaiting_series_name"):
        series_name = update.message.text
        add_series(series_name, update.effective_user.id)
        context.user_data["awaiting_series_name"] = False
        await update.message.reply_text(f"Series '{series_name}' created!")
        context.user_data["current_series"] = series_name
        await handle_series(update, context)


async def graph_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    series_name = context.user_data.get("current_series")
    if not series_name:
        await update.callback_query.edit_message_text("No series selected.")
        return

    keyboard = [
        [InlineKeyboardButton("Day", callback_data="graph_day")],
        [InlineKeyboardButton("Week", callback_data="graph_week")],
        [InlineKeyboardButton("Weekday", callback_data="graph_weekday")],
        [InlineKeyboardButton("Month", callback_data="graph_month")],
        [InlineKeyboardButton("Year", callback_data="graph_year")],
        [InlineKeyboardButton("All Time", callback_data="graph_all")],
        [InlineKeyboardButton("Back", callback_data=f"choose_{series_name}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.edit_message_text("Choose a time period for the graph:", reply_markup=reply_markup)


def main():
    init_db()
    app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Bot is running...")
    app.run_polling()


if __name__ == '__main__':
    main()
