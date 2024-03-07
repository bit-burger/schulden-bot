import json

import discord
from discord import app_commands
from peewee import SqliteDatabase

db = SqliteDatabase("test.db", pragmas={'foreign_keys': 1})

config = json.load(open('config.json', "r"))
token = config["secret"]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

commands = []