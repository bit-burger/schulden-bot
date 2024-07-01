from database.settings import *
from .utils.database_utils import *
from .utils.application_view import *
from .utils.formatting import *
from config import tree
from discord import ui, ButtonStyle
from functools import partial
import discord


@tree.command(name='settings', description="open settings", guild=discord.Object(config.test_guild_id) if config.test_guild_id else None)
async def settings(interaction: discord.Interaction):
    user = check_register(interaction)
    await run_application(interaction, SettingsView(user))




class SettingsView(UserApplicationView):

    def __init__(self, user: User):
        super().__init__(user, ephemeral=True)
        self.setting = Setting.whitelisting_on

    async def setting_select_changed(self, i: discord.Interaction, s: ui.Select):
        self.setting = Setting(int(s.values[0]))
        await self.set_state(i)

    def format_setting_value(self, value: Any):
        if self.setting == Setting.max_amount:
            return "**" + format_euro(value) + "**"
        if value:
            return "**✅ yes**"
        return "**❌ no**"

    async def change_bool_value(self, i: discord.Interaction, b):
        set_setting(self.user, self.setting, not get_setting(self.user, self.setting))
        await self.set_state(i)

    async def change_int_value(self, val, i: discord.Interaction, b):
        set_setting(self.user, self.setting, val)
        await self.set_state(i)

    def render_controls(self, value: Any):
        if self.setting == Setting.max_amount:
            for amount in [1000, 5000, 10000, 50000, 100000]:
                yield Button(
                    style=ButtonStyle.green, label=format_euro(amount), disabled=amount == value,
                    _callable=partial(self.change_int_value, amount)
                )
            return
        yield Button(emoji="✅", style=ButtonStyle.green, label="yes", disabled=value, _callable=self.change_bool_value)
        yield Button(emoji="❌", style=ButtonStyle.red, label="no", disabled=not value, _callable=self.change_bool_value)

    def render(self) -> Iterator[str | discord.Embed | ui.Item]:
        options = list(map(lambda setting: discord.SelectOption(description=setting_short_descriptions[setting],
                                                                value=str(setting.value), label=setting_names[setting],
                                                                default=self.setting == setting), setting_order))
        embed = discord.Embed()
        embed.description = "### " + setting_names[self.setting] + "\n"
        embed.description += f"> {setting_long_descriptions[self.setting]}\n\n"
        value = get_setting(self.user, self.setting)
        embed.description += f"**Current:** \n{self.format_setting_value(value)}"
        yield embed
        yield Select(options=options, row=0, _callable=self.setting_select_changed)
        yield from self.render_controls(value)
