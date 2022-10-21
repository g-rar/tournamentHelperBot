from dotenv import load_dotenv
import os
load_dotenv()

import logging
from bot import bot

# import to register commands
import commands

# import to register game modules
import games.tetrio
import games.generic

if os.getenv("DEV"):
    import devCommands

# logging.basicConfig(level=logging.INFO,format="%(asctime)s - %(funcName)s:%(lineno)d - %(levelname)s: %(message)s", filename="output.log", filemode="a")

def main():
    bot.start()

if __name__ == "__main__":
    main()