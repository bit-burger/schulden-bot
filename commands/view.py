import discord

from config import tree


@tree.command(name='view', description="history of debt with single person",
              guild=discord.Object(id=1201588191094906890))
async def view(interation: discord.Interaction):
    ...
