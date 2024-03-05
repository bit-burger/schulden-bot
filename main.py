import discord
import config


@config.client.event
async def on_ready():
    await config.tree.sync(guild=discord.Object(id=1201588191094906890))
    print(f'We have logged in as {config.client.user}')


@config.client.event
async def on_message(message: discord.Message):
    import random
    content = 'schulderinos 😎'
    if bool(random.getrandbits(1)):
        content = 'schulderinos 🤙'
    if not message.author.bot and message.author != config.client and config.client.user.mentioned_in(message):
        await message.reply(content)


config.client.run(config.token)
