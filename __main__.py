from dotenv import load_dotenv
import os
load_dotenv()

import logging
from bot import bot

# import to register commands
import commands

logging.basicConfig(level=logging.INFO,format="%(asctime)s - %(funcName)s:%(lineno)d - %(levelname)s: %(message)s", filename="output.log", filemode="a")


if __name__ == "__main__":
    bot.run(os.getenv("BOT_TOKEN"))
    