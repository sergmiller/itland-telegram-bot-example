import logging
import json


from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    Filters
)


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


ENV_FILE = ".env"

ASK_BIO, ASK_PHOTO, ASK_LOCATION, ASK_SHOW_WEATHER = range(4)

async def start(update: Update, context) -> int:
    user = update.message.from_user
    logger.info("Start bot for user {}".format(user))
    await update.message.reply_text("Hello, to start using bot please tell about yourself")
    return ASK_BIO

async def ask_bio(update: Update, context) -> int:
    user = update.message.from_user
    message = update.message.text
    logger.info("Ask bio for user {}, got {}".format(user, message))
    return ConversationHandler.END



async def cancel(update, context):
        user = update.message.from_user
        logger.info("User %s canceled the conversation.", user.first_name)
        return ConversationHandler.END




def run_bot(api_token):
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    updater = Updater(api_token)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_BIO: [MessageHandler(Filters.text, ask_bio)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dispatcher.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


def parse_env_params() -> dict:
    data = ""
    with open(ENV_FILE, "r") as f:
        for line in f:
            data += line
    return json.loads(data)


def main():
    env_params = parse_env_params()
    run_bot(env_params["API_KEY"])


if __name__ == "__main__":
    main()
