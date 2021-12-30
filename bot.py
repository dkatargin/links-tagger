import nltk
import requests
import validators
from bs4 import BeautifulSoup
from nltk.tokenize import RegexpTokenizer
from telegram.ext import Updater, Filters, MessageHandler

from common import config, logger

tokenizer = RegexpTokenizer(r'\w+')


def process_data(text):
    target_text = text
    if validators.url(text.strip()):
        req = requests.get(text, headers={'User-Agent': 'TelegramBot (like TwitterBot)'})
        content = req.content[:100000]
        soup = BeautifulSoup(content, "html.parser")
        words = ""
        html_title = soup.find("title")
        og_descr = soup.find("meta", property="og:description")
        twitter_descr = soup.find("meta", property="twitter:description")
        if html_title and len(html_title.contents) != 0:
            words += html_title.contents[0]
        if og_descr and len(og_descr.contents) != 0:
            words += og_descr.contents[0]
        if twitter_descr and len(twitter_descr.contents) != 0:
            words += twitter_descr.contents[0]
        target_text = words

    tokenized = tokenizer.tokenize(target_text)
    is_noun = lambda pos: pos[:2] == 'NN'
    tags = sorted(set([word.lower() for (word, pos) in nltk.pos_tag(tokenized) if is_noun(pos)]))
    return tags


def main(update, context):
    data = update.message.text
    if update.message.chat.id != int(config.config.get("Telegram", "admin_id")):
        logger.bot_logger.warning(f"request from unauthorized user-id {update.message.chat.id}")
        return
    tags = process_data(data)
    result = ""
    for t in tags:
        result += f"#{t} "

    update.message.reply_text(result)


if __name__ == "__main__":
    logger.bot_logger.info("bot running...")
    updater = Updater(config.config.get("Telegram", "token"))
    updater.dispatcher.add_handler(MessageHandler(Filters.all, main))
    updater.start_polling()
    updater.idle()
