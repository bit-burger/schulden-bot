import discord
import config
import commands
from database import init

init()

@config.client.event
async def on_ready():
    await config.tree.sync(guild=discord.Object(id=1201588191094906890))
    print(f'We have logged in as {config.client.user}')


@config.client.event
async def on_message(message: discord.Message):
    if message.author != config.client and config.client.user.mentioned_in(message):
        await message.channel.send('schulderinos 😎')


config.client.run(config.token)
