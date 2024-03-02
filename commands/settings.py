import discord

from database import RegisteredUser
from .util import check_register
from config import tree
from discord import ui, Interaction


@tree.command(name='settings', description="open settings", guild=discord.Object(id=1201588191094906890))
async def settings(interaction: discord.Interaction):
    user = check_register(interaction)
    embed = discord.Embed(title="Settings", description="Your settings will be saved automatically", colour=discord.Colour.dark_gray())
    await interaction.response.send_message(embed=embed, view=Settings(user))


class Settings(discord.ui.View):
    def __init__(self, user: RegisteredUser):
        super().__init__()

        self.add_item(OpenToEveryoneSelect(user))


class OpenToEveryoneSelect(ui.Select):
    def __init__(self, user: RegisteredUser):
        options = [discord.SelectOption(value="1", label="Open to track debt with everyone",
                                        description="everyone can track your debt, except those that you /ignore",
                                        default=user.everyone_allowed_per_default),
                   discord.SelectOption(value="0", label="Only whitelisted (default)",
                                        description="only track debt with whitelisted users (with /whitelist)",
                                        default=not user.everyone_allowed_per_default)]

        self.user = user
        super().__init__(options=options)

    async def callback(self, interaction: Interaction):
        self.user.everyone_allowed_per_default = self.values[0] == "1"
        self.user.save()
        await interaction.response.send_message(embed=discord.Embed(title="Settings saved!"))
