import json

import discord
from discord import app_commands
from peewee import SqliteDatabase

db = SqliteDatabase("test.db", pragmas={'foreign_keys': 1})

config = json.load(open('config.json', "r"))
token = config["secret"]

plus_emoji_id = config["plus_emoji_id"]
plus_emoji = f"<:plus:{plus_emoji_id}>"
minus_emoji_id = config["minus_emoji_id"]
minus_emoji = f"<:minus:{minus_emoji_id}>"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

commands = []