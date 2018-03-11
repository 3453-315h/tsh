#!/usr/bin/python


import telepot
from pprint import pprint
import config




bot = telepot.Bot(config.bot_token)


response = bot.getUpdates()

# Print all raw messages with chat_id,text,type,username
pprint(response)
