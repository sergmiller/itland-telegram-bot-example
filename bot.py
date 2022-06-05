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

def start(update: Update, context) -> int:
    user = update.message.from_user
    logger.info("Start bot for user %s, with username %s and lang code %s",
                user.first_name, user.username, user.language_code)
    update.message.reply_text("Hello, to start using bot please tell about yourself")
    return ASK_BIO

def got_bio(update: Update, context) -> int:
    user = update.message.from_user.username
    message = update.message.text
    logger.info("Ask bio for user %s, got %s", user, message)
    update.message.reply_text(
        'Now, send me your photo please, or send /skip if you don\'t want to.'
    )
    return ASK_PHOTO


def got_photo(update: Update, context) -> int:
    user = update.message.from_user.username
    photo_file = update.message.photo[-1].get_file()
    photo_file.download('photo_{}.jpg'.format(user))
    logger.info("Photo of %s: %s", user, 'photo_{}.jpg'.format(user))
    send_ask_location_message(update)
    return ASK_LOCATION

def skip_photo(update: Update, context) -> int:
    user = update.message.from_user.username
    logger.info("User %s, skip photo uploading", user)
    send_ask_location_message(update)
    return ASK_LOCATION


def send_ask_location_message(update):
    update.message.reply_text(
        'OK, send me your location please or type your city to get a weather report.'
    )


def got_location(update: Update, context) -> int:
    user = update.message.from_user.username
    user_location = update.message.location
    logger.info(
        "Location of %s: %f / %f", user, user_location.latitude, user_location.longitude
    )
    return send_report(update, user_location.latitude, user_location.longitude, None)

def got_location_from_text(update: Update, context) -> int:
    user = update.message.from_user.username
    message = update.message.text
    logger.info(
        "Location of %s: %s", user, message
    )
    return send_report(update, None, None, message)


def send_report(update, lat, lon, city):
    CITY_COORDINATES = {
        "Moscow": (55.644466, 37.395744),
        "London": (51.507359, -0.136439),
    }

    if city is not None:
        assert lat is None and lon is None
        lat, lon = CITY_COORDINATES.get(city, CITY_COORDINATES["Moscow"])

    import requests

    r = requests.get("https://api.open-meteo.com/v1/forecast?latitude={}&longitude={}&hourly=temperature_2m".format(lat, lon))
    if r.status_code != 200:
        update.message.reply_text("Problems with your weather request, try later")
        return ConversationHandler.END

    report = json.loads(r.content)

    # WEATHER REPORT EXAMPLE:
    #
    # {"hourly": {
    #     "time": ["2022-06-04T00:00", "2022-06-04T01:00", "2022-06-04T02:00", "2022-06-04T03:00", "2022-06-04T04:00",
    #              "2022-06-04T05:00", "2022-06-04T06:00", "2022-06-04T07:00", "2022-06-04T08:00", "2022-06-04T09:00"],
    #     "temperature_2m": [8.6, 8.3, 8.6, 10, 11.9, 13.8, 16.2, 17.5, 18.3, 18.9, 19.1, 19.4, 20.2, 20.3, 20.2, 19.8,
    #                        13.3, 13, 13.3, 13.9, 15.3, 16.9, 19, 21.4, 22.8, 23.8, 25, 25.6, 26.1, 26.4, 26.5, 26.4,
    #                        25.7, 24.4, 22.7, 20.6, 19.7, 18.9, 18, 17.3, 16.6]}, "utc_offset_seconds": 0,
    #  "latitude": 55.625, "elevation": 185.5, "generationtime_ms": 1.6069412231445312,
    #  "hourly_units": {"time": "iso8601", "temperature_2m": "\xc2\xb0C"}, "longitude": 37.375}

    times = report["hourly"]["time"]
    temps = report["hourly"]["temperature_2m"]
    import datetime
    d = datetime.datetime.utcnow().replace(minute=0).isoformat()
    cur_time = ':'.join(d.split(':')[:-1])
    next_tmp = None
    for tm, tp in zip(times, temps):
        if tm > cur_time:
            next_tmp = tp
            break

    if next_tmp is None:
        update.message.reply_text("Problems with your weather request, try later")
        return ConversationHandler.END

    update.message.reply_text(
        'Your weather report for next hour: {}'.format(next_tmp)
    )
    return ConversationHandler.END



def cancel(update, context):
    user = update.message.from_user.username
    logger.info("User % canceled the conversation.", user)
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
            ASK_BIO: [MessageHandler(Filters.text, got_bio)],
            ASK_PHOTO: [MessageHandler(Filters.photo, got_photo), CommandHandler('skip', skip_photo)],
            ASK_LOCATION: [MessageHandler(Filters.location, got_location), MessageHandler(Filters.text, got_location_from_text)],
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
