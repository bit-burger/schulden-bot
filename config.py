import json

import discord
from discord import app_commands
from peewee import SqliteDatabase

import logging

logger = logging.getLogger('peewee')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.DEBUG)

db = SqliteDatabase("test.db", pragmas={'foreign_keys': 1})

config = json.load(open('config.json', "r"))
token = config["secret"]

plus_emoji_id = config["plus_emoji_id"]
plus_emoji = f"<:plus:{plus_emoji_id}>"
minus_emoji_id = config["minus_emoji_id"]
minus_emoji = f"<:minus:{minus_emoji_id}>"

help_icon_url = "https://cdn.discordapp.com/attachments/1213483785593819186/1215785651098746890/Infobox_info_icon_white.svg.png?ex=65fe039f&is=65eb8e9f&hm=f921294c968990f6593b6ad66a83d8e080aaaf73bc18625ec100e0db7b7111dd&"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

commands = []
