from telegram.ext import Updater, Filters, MessageHandler

from common import config, logger


def process_data(text):
    text_type = "text"



def main(update, context):
    data = update.message.text
    if update.message.chat.id != int(config.config.get("Telegram", "admin_id")):
        logger.bot_logger.warning(f"request from unauthorized user-id {update.message.chat.id}")
        return
    process_data(data)


if __name__ == "__main__":
    logger.bot_logger.info("bot running...")
    updater = Updater(config.config.get("Telegram", "token"))
    updater.dispatcher.add_handler(MessageHandler(Filters.all, main))
    updater.start_polling()
    updater.idle()
