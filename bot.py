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

# lang names for NLTK
ru_lang = "rus"
en_lang = "eng"

# tokenizer for words without spec-symbols
tokenizer = RegexpTokenizer(r'\w+')

# init language detection
tc = nltk.classify.textcat.TextCat()

# load lemmatizers
en_lemmatizer = WordNetLemmatizer()
ru_lemmatizer = Mystem()


def get_acronyms(text):
    return re.findall(r"\b[A-Z]{2,}\b", text)


def get_lang(text):
    """
    Detect language and return on of: rus,eng
    :param text: any string
    :return: string: rus or eng
    """
    lang = str(tc.guess_language(text)).strip()
    if lang not in [ru_lang, en_lang]:
        return en_lang
    return lang


def lemmatize_word(word, lang):
    """
    Get lemma for word by selected language. For ru-lang use mystem lemmatizer and NLTK for others
    :param word: any word from text
    :param lang: rus or eng
    :return: return list of lemmas (words)
    """
    if lang == ru_lang:
        res = ru_lemmatizer.lemmatize(word)[0]
    else:
        res = en_lemmatizer.lemmatize(word, "n")
    return res


def is_tag_pos(pos):
    """
    Check word type. We needed only nouns or NONLEX (S is russian noun-word)
    :param pos:
    :return:
    """
    if pos in ["S", "NONLEX"] or pos[:2] == "NN":
        return True
    return False


def process_data(text):
    """
    Process text data. Gets telegram message on input and return tags. In input is url make http-request and parse page
    meta info .
    :param text: telegram message
    :return: tags: sorted and deduplicated list of tags
    """
    # check if text is url
    if validators.url(text.strip()):
        # make request as TelegramBot for better structured meta data
        req = requests.get(text, headers={'User-Agent': 'TelegramBot (like TwitterBot)'})
        req.close()
        content = req.content[:100000]
        # parse html and get content from meta tags
        soup = BeautifulSoup(content, "html.parser")
        text = ""
        html_title = soup.find("title")
        og_descr = soup.find("meta", property="og:description")
        twitter_descr = soup.find("meta", property="twitter:description")
        if html_title and len(html_title.contents) != 0:
            text += html_title.contents[0]
        if og_descr and len(og_descr.contents) != 0:
            text += og_descr.contents[0]
        if twitter_descr and len(twitter_descr.contents) != 0:
            text += twitter_descr.contents[0]

    # init variables for text prepare
    target_text = ""
    text_lang = get_lang(text)
    acronyms = get_acronyms(text)
    # convert word case to lower, except acronyms. It needed for better pos detection.
    for w in text.split():
        if w in acronyms:
            target_text += f"{w} "
        else:
            target_text += f"{w.lower()} "
    # get tokens from text
    tokenized = tokenizer.tokenize(target_text)
    # get pos of words in text and store only nouns in lower-case
    tags = sorted(set(
        [lemmatize_word(word.lower(), text_lang) for (word, pos) in nltk.pos_tag(tokenized, lang=text_lang) if
         is_tag_pos(pos)]))
    return tags


def main(update, context):
    """
    Main func for handle telegram messages. Return text-message as result
    :param update: telegram object (message or any)
    :param context: telegram context
    :return:
    """
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
