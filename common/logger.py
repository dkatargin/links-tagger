import logging

FORMAT = '%(asctime)s %(name)s <%(levelname)s> %(message)s'
logging.basicConfig(format=FORMAT)
bot_logger = logging.getLogger("telegram-bot")
