import re
from pathlib import Path

import nltk

# Переопределяем путь к данным NLTK — храним внутри проекта, а не в $HOME/nltk_data
_NLTK_DATA = Path(__file__).parent / "nltk_data"
_NLTK_DATA.mkdir(exist_ok=True)
nltk.data.path = [str(_NLTK_DATA)]

import requests
import validators
from bs4 import BeautifulSoup
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tokenize import RegexpTokenizer
import pymorphy3
from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

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
ru_lemmatizer = pymorphy3.MorphAnalyzer()


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


def extract_ru_nouns(words):
    """
    Лемматизация и фильтрация существительных для смешанного текста.
    - Кириллические слова: pymorphy3 (POS OpenCorpora, NOUN)
    - Латинские слова (POS=None у pymorphy3): передаём батчем в NLTK pos_tag
    :param words: список токенов в нижнем регистре
    :return: список лемм существительных
    """
    result = []
    # разделяем кириллицу и латиницу
    latin_words = [w for w in words if w.isascii()]
    for word in words:
        if not word.isascii():
            # кириллица — pymorphy3
            parsed = ru_lemmatizer.parse(word)[0]
            pos = parsed.tag.POS
            logger.bot_logger.info(f"word-pos (ru): {word} {pos}")
            if pos == "NOUN":
                result.append(parsed.normal_form)
        # латинские обрабатываем батчем ниже

    # латинские слова — один вызов pos_tag для всего батча (эффективнее)
    if latin_words:
        for word, pos in nltk.pos_tag(latin_words):
            logger.bot_logger.info(f"word-pos (en in ru-text): {word} {pos}")
            if is_en_noun(pos, word):
                result.append(lemmatize_word(word.lower()))

    return result


def lemmatize_word(word):
    """
    Лемматизация английского слова через WordNet (только существительные).
    :param word: токен в нижнем регистре
    :return: лемма
    """
    return en_lemmatizer.lemmatize(word, "n")


def is_en_noun(pos, word):
    """
    Фильтр существительных для английского по тегам NLTK (Penn Treebank).
    :param pos: тег от nltk.pos_tag
    :param word: строка для дебага
    :return: bool
    """
    # NN, NNS, NNP, NNPS — все формы существительных в Penn Treebank
    return pos.startswith("NN")


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
        if html_title and (len(html_title.contents) != 0 or html_title.attrs.get("content")):
            tag_content = html_title.attrs.get("content") or html_title.contents[0]
            text += tag_content + " "
        if og_descr and (len(og_descr.contents) != 0 or og_descr.attrs.get("content")):
            tag_content = og_descr.attrs.get("content") or og_descr.contents[0]
            text += tag_content + " "
        if twitter_descr and (len(twitter_descr.contents) != 0 or twitter_descr.attrs.get("content")):
            tag_content = twitter_descr.attrs.get("content") or twitter_descr.contents[0]
            text += tag_content + " "

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

    if text_lang == ru_lang:
        # pymorphy3 даёт лемму и POS за один проход — NLTK pos_tag не нужен
        nouns = extract_ru_nouns(tokenized)
    else:
        # для EN используем NLTK Penn Treebank теги
        tagged = nltk.pos_tag(tokenized)
        nouns = []
        for word, pos in tagged:
            logger.bot_logger.info(f"word-pos (en): {word} {pos}")
            if is_en_noun(pos, word):
                nouns.append(lemmatize_word(word.lower()))

    tags = sorted(set(nouns))
    return tags


async def main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Main func for handle telegram messages. Return text-message as result
    :param update: telegram object (message or any)
    :param context: telegram context
    :return:
    """
    if not update.message:
        return
    result = ""
    send_to_chan = config.config.get("Telegram", "send_to")
    data = update.message.text
    if update.message.chat.id != int(config.config.get("Telegram", "admin_id")):
        logger.bot_logger.warning(f"request from unauthorized user-id {update.message.chat.id}")
        return
    try:
        tags = process_data(data)
        for t in tags:
            result += f"#{t} "
        if send_to_chan:
            await context.bot.send_message(chat_id=send_to_chan, text=f"{data}\n{result}", parse_mode='HTML')
    except Exception as e:
        result = f"Ошибка: {e}"

    await update.message.reply_text(result)


if __name__ == "__main__":
    logger.bot_logger.info("bot running...")
    application = Application.builder().token(config.config.get("Telegram", "token")).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, main))
    application.run_polling()
