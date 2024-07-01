from database.database_schema import WhitelistUser
from database.settings import *
from .utils.application_view import *
from .utils.formatting import *
from .utils.database_utils import *
from .utils.discord_utils import *
from config import tree
from discord import ui, ButtonStyle, app_commands

whitelist_group = app_commands.Group(description="asd", name="whitelist",
                                     guild_ids=[config.test_guild_id] if config.test_guild_id else None)
tree.add_command(whitelist_group)


@whitelist_group.command(name="view", description="view all whitelisted users")
async def whitelist_view(interaction: discord.Interaction):
    user = check_register(interaction)
    if not get_setting(user, Setting.whitelisting_on):
        return await interaction.response.send_message(embed=discord.Embed(title="Whitelisting is not enabled",
                                                                           description="Use **/settings** to turn on whitelisting",
                                                                           color=0xFF0000), ephemeral=True)
    whitelisted_ids = set(map(lambda whitelisted: whitelisted.whitelisted.id, user.whitelisted))
    return await interaction.response.send_message(
        embed=discord.Embed(title="All whitelisted users:", description=id_iter_to_text(whitelisted_ids)),
        ephemeral=True)


@whitelist_group.command(name="reset", description="clear whitelist (will not delete any debt information)")
async def whitelist_reset(interaction: discord.Interaction):
    user = check_register(interaction)
    await interaction.response.send_message(view=WhitelistUserReset(user),
                                            embed=discord.Embed(title="Do you want to reset your whitelist?",
                                                                description="Are you sure that you want to reset your whitelist, this is not reversable",
                                                                color=0xFF0000))


@whitelist_group.command(name="remove", description="remove people from whitelist")
async def whitelist_remove(interaction: discord.Interaction):
    user = check_register(interaction)
    await run_application(interaction, WhitelistRemoveApp(user))


class WhitelistRemoveApp(UserApplicationView):

    def __init__(self, user: User):
        super().__init__(user)
        self.state = "selecting"
        self.to_be_un_whitelisted = set()
        self.already_not_whitelisted = set()

    async def select(self, i, s: UserSelect):
        whitelisted = set(map(lambda whitelisted: whitelisted.whitelisted.id, self.user.whitelisted))
        to_be_un_whitelisted = set(to_id_set(filter(lambda user: not user.bot and user.id != self.user.id, s.values)))
        self.already_not_whitelisted = to_be_un_whitelisted - whitelisted
        to_be_un_whitelisted &= whitelisted
        self.to_be_un_whitelisted |= to_be_un_whitelisted
        self.state = "reviewing"
        await self.set_state(i)

    async def add_more(self, i, b):
        self.state = "selecting"
        await self.set_state(i)

    async def cancel(self, i, b):
        self.stop()
        self.state = "fail"
        await self.set_state(i)

    async def confirm(self, i, b):
        self.stop()
        WhitelistUser.delete().where(
            WhitelistUser.whitelisted.in_(self.to_be_un_whitelisted), WhitelistUser.by == self.user).execute()
        self.state = "success"
        await self.set_state(i)

    def render(self) -> Iterator[str | discord.Embed | ui.Item]:
        if self.state == "selecting":
            embed = discord.Embed(title="Select users to remove from whitelist")
            if len(self.to_be_un_whitelisted) > 0:
                embed = discord.Embed(title="Select more users to remove from whitelist")
                embed.add_field(name="Already being added", value=id_iter_to_text(self.to_be_un_whitelisted))
            yield embed
            yield UserSelect(self.select, max_values=25, placeholder="who to remove from your whitelist")
        if self.state == "reviewing":
            embed = discord.Embed(title="No users have been selected")
            if len(self.to_be_un_whitelisted) > 0:
                embed = discord.Embed(title="Confirm users to be removed from whitelist")
                embed.add_field(name="Users that will be removed:", value=id_iter_to_text(self.to_be_un_whitelisted))
                yield Button(style=ButtonStyle.green, label="confirm", _callable=self.confirm)
            if len(self.already_not_whitelisted) > 0:
                embed.add_field(name="Users that have not been whitelisted (will be ignored):",
                                value=id_iter_to_text(self.already_not_whitelisted))
            yield embed
            yield Button(style=ButtonStyle.red, label="cancel", _callable=self.cancel)
            yield Button(style=ButtonStyle.blurple, label="Select more users to remove from whitelist",
                         _callable=self.add_more)
        if self.state == "success":
            yield discord.Embed(title="You have successfully removed users from your whitelist",
                                description="Removed from your whitelist: " + id_iter_to_text(
                                    self.to_be_un_whitelisted),
                                color=0x00FF00)
        if self.state == "fail":
            yield discord.Embed(title="Nobody has been removed from your whitelist",
                                color=0xFF0000)


class WhitelistUserReset(ui.View):
    def __init__(self, user: User):
        super().__init__()
        self.user = user

    @ui.button(label="Reset whitelist", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        WhitelistUser.delete().where(WhitelistUser.by == self.user).execute()
        await interaction.response.edit_message(view=ui.View(),
                                                embed=discord.Embed(title="Whitelist has been reset", color=0xFF0000))
        self.stop()

    @ui.button(label="Cancel", style=discord.ButtonStyle.green)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        interaction.response.edit_message(view=ui.View(),
                                          embed=discord.Embed(title="Whitelist has not been reset", color=0x00FF00))
        self.stop()


@whitelist_group.command(name='add', description="whitelist users to track debt")
async def whitelist(interaction: discord.Interaction):
    user = check_register(interaction)
    if not get_setting(user, Setting.whitelisting_on):
        return await interaction.response.send_message(embed=discord.Embed(title="Whitelisting is not enabled",
                                                                           description="Use **/settings** to turn on whitelisting",
                                                                           color=0xFF0000), ephemeral=True)
    embed = discord.Embed(title="Select users to whitelist")
    await interaction.response.send_message(embed=embed, view=WhitelistMenu(user, set()), ephemeral=True)


class WhitelistMenu(discord.ui.View):
    def __init__(self, user: User, already_selected_ids: {int}):
        super().__init__()
        self.add_item(WhitelistSelect(user, already_selected_ids))


class WhitelistSelect(ui.MentionableSelect):
    def __init__(self, user: User, already_selected_ids: {int}):
        self.user = user
        self.already_selected_ids = already_selected_ids
        super().__init__(min_values=0, placeholder="who do you want to whitelist?", max_values=25)

    async def callback(self, interaction: discord.Interaction):
        self.disabled = True
        users: {discord.User} = set()
        for value in self.values:
            if isinstance(value, discord.User):
                users.add(value)
            if isinstance(value, discord.Member):
                users.add(value)
            if isinstance(value, discord.Role):
                users.update(value.members)
        users = set(filter(lambda user: not user.bot and user.id != self.user.id, users))
        user_ids = to_id_set(users) | self.already_selected_ids
        ignored_ids = user_ids & set(map(lambda ignored: ignored.ignored.id, self.user.ignored))
        whitelisted_ids = user_ids & set(
            map(lambda whitelisted: whitelisted.whitelisted.id, self.user.whitelisted))
        user_ids -= ignored_ids | whitelisted_ids
        embed = discord.Embed(title="Confirm whitelisting", color=0x00ff00)
        if len(user_ids) > 0:
            embed.add_field(name="Whitelist:",
                            value=id_iter_to_text(user_ids), inline=False)
        else:
            embed = discord.Embed(title="No one new has been selected for whitelisting", color=0xff0000)
        if len(whitelisted_ids) > 0:
            embed.add_field(name="Already whitelisted (will be ignored):",
                            value=id_iter_to_text(whitelisted_ids))
        if len(ignored_ids) > 0:
            embed.add_field(name="Ignored (can not be whitelisted):",
                            value=id_iter_to_text(ignored_ids))
        if len(user_ids) == 0:
            return await interaction.response.edit_message(view=NoAddedToWhitelist(self.user), embed=embed)
        await interaction.response.edit_message(
            view=WhitelistConfirmation(user=self.user, users=user_ids, embed=embed),
            embed=embed)


class NoAddedToWhitelist(ui.View):

    def __init__(self, user: User):
        super().__init__()
        self.user = user

    @ui.button(label="Whitelist more users", style=discord.ButtonStyle.blurple)
    async def whitelist(self, interaction: discord, button: discord.ui.Button):
        embed = discord.Embed(title="Select users to whitelist")
        await interaction.response.edit_message(embed=embed, view=WhitelistMenu(self.user, set()))

    @ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord, button: discord.ui.Button):
        embed = discord.Embed(title="Nobody has been whitelisted", color=discord.Color.red())
        await interaction.response.edit_message(embed=embed, view=ui.View())


class WhitelistConfirmation(ui.View):

    def __init__(self, user: User, users: [User], embed: discord.Embed):
        super().__init__()
        self.embed = embed
        self.user = user
        self.user_ids = users

    @ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="Whitelisted successfully", color=0x00FF00)
        embed.add_field(name="Users whitelisted: ", value=self.embed.fields[0].value, inline=False)
        await interaction.response.edit_message(embed=embed, view=ui.View())
        self.stop()
        for user_id in self.user_ids:
            user = check_register_from_id(user_id)
            WhitelistUser.create(by=self.user, whitelisted=user)

    @ui.button(label="No", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(view=ui.View(),
                                                embed=discord.Embed(title="You have not whitelisted anybody",
                                                                    colour=0xFF0000))
        self.stop()

    @ui.button(label="Whitelist more users", style=discord.ButtonStyle.blurple)
    async def whitelist(self, interaction: discord, button: discord.ui.Button):
        embed = discord.Embed(title="Whitelist more users")
        embed.add_field(name="Already whitelisted: ", value=self.embed.fields[0].value, inline=False)
        for field in self.embed.fields[1:]:
            embed.add_field(name=field.name, value=field.value, inline=False)
        await interaction.response.edit_message(embed=embed, view=WhitelistMenu(self.user, self.user_ids))
