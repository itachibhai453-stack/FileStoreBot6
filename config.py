#  Developed by t.me/napaaextra
#  Developed by t.me/napaaextra
import logging
from logging.handlers import RotatingFileHandler
import os 

LOG_FILE_NAME = "bot.log"
PORT = os.environ.get("PORT", "8091")

OWNER_ID = 7653921320
MSG_EFFECT = 5046509860389126442

SHORT_URL = "arolinks.com"
SHORT_API = "97efe163e07453fe37fcd8a36adb284fb2adca2f"
MESSAGES = {
    "SHORT": "https://graph.org/file/d48f3b1c7b41495ce1a0c-4d87ff09137971e900.jpg",
    "SHORTNER_MSG": "<b>🔗 Your files are protected with a shortener!</b>\n\n<b>📺 Watch Tutorial:</b> <a href='{tutorial_link}'>Click Here</a>\n\n<b>🔐 Click the button below to proceed:</b>"
}

def LOGGER(name: str, client_name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    formatter = logging.Formatter(
        f"[%(asctime)s - %(levelname)s] - {client_name} - %(name)s - %(message)s",
        datefmt='%d-%b-%y %H:%M:%S'
    )
    
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.addHandler(stream_handler)

    return logger
