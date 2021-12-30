import re

import nltk
import requests
import validators
from bs4 import BeautifulSoup
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tokenize import RegexpTokenizer
from pymystem3 import Mystem
from telegram.ext import Updater, Filters, MessageHandler

from common import config, logger

ru_lang = "rus"
en_lang = "eng"

tokenizer = RegexpTokenizer(r'\w+')
tc = nltk.classify.textcat.TextCat()

en_lemmatizer = WordNetLemmatizer()
ru_lemmatizer = Mystem()


def get_text_acronyms(text):
    return re.findall(r"\b[A-Z]{2,}\b", text)


def get_lang(text):
    return str(tc.guess_language(text)).strip()


def lemmatize_word(word, lang):
    if lang == ru_lang:
        res = ru_lemmatizer.lemmatize(word)[0]
    else:
        res = en_lemmatizer.lemmatize(word, "n")
    return res


def is_tag_pos(pos):
    if pos in ["S", "NONLEX"] or pos[:2] == "NN":
        return True
    return False


def process_data(text):
    target_text = text
    acronyms = get_text_acronyms(text)
    if validators.url(text.strip()):
        target_text = ""
        req = requests.get(text, headers={'User-Agent': 'TelegramBot (like TwitterBot)'})
        req.close()
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
        for w in words.split():
            if w in acronyms:
                target_text += f"{w} "
            else:
                target_text += f"{w.lower()} "

    text_lang = get_lang(target_text)

    tokenized = tokenizer.tokenize(target_text)
    tags = sorted(set(
        [lemmatize_word(word.lower(), text_lang) for (word, pos) in nltk.pos_tag(tokenized, lang=text_lang) if
         is_tag_pos(pos)]))
    return tags


def main(update, context):
    result = ""
    data = update.message.text
    if update.message.chat.id != int(config.config.get("Telegram", "admin_id")):
        logger.bot_logger.warning(f"request from unauthorized user-id {update.message.chat.id}")
        return
    try:
        tags = process_data(data)
        for t in tags:
            result += f"#{t} "
    except Exception as e:
        result = f"Ошибка: {e}"

    update.message.reply_text(result)


if __name__ == "__main__":
    logger.bot_logger.info("bot running...")
    updater = Updater(config.config.get("Telegram", "token"))
    updater.dispatcher.add_handler(MessageHandler(Filters.all, main))
    updater.start_polling()
    updater.idle()
