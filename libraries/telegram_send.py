import telebot

from config import Config
from libraries.logger import logger


def send_telegram(url):
    if not url:
        logger.error('Empty url. Can\'t send to Telegram')
        return
    try:
        bot = telebot.TeleBot(token=Config.TELEGRAM_BOT_TOKEN)

        message = f'''
🧲 <a href="{url}"><strong>DC Comics URL Token</strong></a>

Useful Links 🔗
<a href="https://nft.dcuniverse.com/login"><strong>DC Universe Queue</strong></a>
<a href="https://www.dcfandome.com/"><strong>DC Fandome</strong></a>
    '''

        bot.send_message(Config.TELEGRAM_ALERT_CHAT, message, parse_mode='html')
        logger.info('[MESSAGE SENT SUCCESSFULLY WITH TELEGRAM!]')
    except Exception as e:
        logger.error(f'[TELEGRAM ERROR]: {e}')
