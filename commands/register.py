import discord

import config
from config import tree
from database import RegisteredUser


# write that this allowes the application to save user data, until unregisertering
@tree.command(name='register', description="register to take part ", guild=discord.Object(id=1201588191094906890))
async def register(interaction: discord.Interaction):
    registered_user_query = RegisteredUser.select().where(RegisteredUser.id == interaction.user.id)
    if registered_user_query.exists():
        return await interaction.response.send_message("You are already registered, to unregister use **/unregister**", ephemeral=True)

    RegisteredUser.create(id=interaction.user.id)
    embed = discord.Embed(title="You are now registered!")
    embed.set_author(name="SchuldenBot", icon_url=config.client.user.display_avatar.url)
    embed.add_field(name="/addfriend", value="to add friends", inline=False)
    embed.add_field(name="/help", value="get help on how to track debt", inline=False)
    embed.add_field(name="/settings", value="to change your default settings", inline=False)
    embed.add_field(name="/unregister", value="to unregister", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)