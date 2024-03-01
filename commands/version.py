import re
from os import read

import discord
import git

import config
from config import tree

repo = git.Repo(search_parent_directories=True)
sha = repo.head.object.hexsha

description = open("version.txt", "r")
version = description.read()
major_version = re.findall(r'^\d', version[1:])[0]

description = open("description.txt", "r")
description = description.read()



@tree.command(name='version', description="gives version information", guild=discord.Object(id=1201588191094906890))
async def schulden(interaction: discord.Interaction):
    embed = discord.Embed(title="SchuldenBot V" + major_version,
                          description="full version: **" + version + "**-" + sha)
    # embed.set_author(name="SchuldenBot", icon_url=config.client.user.display_avatar.url)
    embed.set_footer(text=description)
    await interaction.response.send_message(embed=embed)
