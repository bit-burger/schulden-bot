import asyncio
from typing import Literal, Optional

from discord import app_commands, ButtonStyle
from discord.ui.dynamic import DynamicItem

from .attachment import image_listener
from .utils.formatting import *
from commands.utils.application_view import *
from commands.utils.database_utils import *
from commands.utils.discord_utils import send_error_embed
from config import tree, trash_can_emoji, help_icon_url
from database.groups import *


@tree.command(name='view', description="history of debt with single person",
              guild=discord.Object(id=1201588191094906890))
@app_commands.autocomplete()
@app_commands.rename(unique_id="unique_id")
@app_commands.describe(show="if this slash command should be viewable from outside (change default in /settings)",
                       unique_id="the unique id of the debt/payment entry you want to view")
async def view(interaction: discord.Interaction, unique_id: str, show: Optional[Literal['yes', 'no']] = None):
    user = check_register(interaction)
    if is_group_id(unique_id):
        ephemeral = ephemeral_group_from_arg(user, show)
    else:
        ephemeral = ephemeral_from_arg(user, show)
    if not is_valid_id(unique_id):
        return await send_error_embed(interaction, title="Error", description="not a valid id")
    if not get_group(unique_id, user) and not get_sub_group(unique_id, user):
        return await send_error_embed(interaction, "Not found",
                                      description=f"debt entry does not exist with id `{unique_id}` "
                                                  "or you do not have any permission to access this entry")

    await run_application(interaction, DebtView(user, unique_id, ephemeral))


class DebtView(UserApplicationView):

    def __init__(self, user: User, unique_id: str, ephemeral, group=None, sub_groups=None, participant=None):
        self.unique_id = unique_id
        super().__init__(user, ephemeral)
        self.group = group
        self.sub_groups = sub_groups
        self.participant = participant
        if not group or not sub_groups or not participant:
            self.set_group_and_subgroups()
        image_listener.add_listener(self.user.id, self)
        if self.group.type == "credit":
            self.name = "debt entry"
        elif self.group.type == "group_credit":
            self.name = "group debt entry"
        elif self.group.type == "money_give":
            self.name = "payment entry"
        else:
            raise "embed type does not exist"
        self.is_deleted = False

    def set_group_and_subgroups(self):
        self.group = get_group(self.unique_id, self.user)
        self.sub_groups = [*self.group.sub_groups]
        self.participant = get_participant(self.unique_id, self.user)

    def render(self) -> Iterator[str | discord.Embed | ui.Item]:
        if is_group_id(self.unique_id):
            yield from self.render_group()
        else:
            yield from self.render_sub_group()

    def render_sub_group(self):
        sub_group = get_sub_group(self.unique_id, self.user)

    async def change_description(self, i, b):
        await i.response.send_modal(DescriptionModal(self, self.group.description))

    async def change_description_confirm(self, i, description):
        self.group.description = description
        self.group.description_edited = True
        self.group.save()
        await self.set_state(i)

    async def delete_description(self, i, b):
        self.group.description = None
        self.group.description_edited = True
        self.group.save()
        await self.set_state(i)

    async def delete_picture(self, i, b):
        self.group.image_url = None
        self.group.image_url_edited = True
        self.group.save()
        await self.set_state(i)

    async def event(self, event):
        interaction = event[0]
        self.group.image_url = event[1]
        self.group.image_url_edited = True
        self.group.save()
        await asyncio.gather(
            run_application(interaction, self),
            self.last_interaction.delete_original_response()
        )

    async def delete(self, i: discord.Interaction, b):
        await i.response.send_message(
            embed=discord.Embed(title="confirm", description=f"do you really want to delete this {self.name}?",
                                color=0xFF0000),
            view=DeleteConfirm(uid=self.unique_id, name=self.name, view=self, ephemeral=self.ephemeral,
                               subgroups=self.sub_groups, user=self.user))

    async def delete_confirmed(self):
        if not self.is_deleted:
            await self.last_interaction.delete_original_response()
            self.clean_up()

    async def request_delete(self, i, b):
        ...

    def render_group(self):
        deleted = all(map(lambda s_g: s_g.deleted_at is not None, self.sub_groups))
        # edited = any(map(lambda s_g: s_g.edited is True, self.sub_groups)) or self.group.description_edited
        embed = discord.Embed(color=0xFF0000 if deleted else None)

        embed.description = "### " + self.name

        if deleted:
            embed.description += f" {trash_can_emoji} (deleted)"
        # elif edited:
        #     embed.description += f" ✏️ (edited)"
        embed.description += "\n"

        if self.group.type == "money_give" or self.group.type == "credit":
            sub_group = self.sub_groups[0]
            money_write = sub_group.money_writes.where(MoneyWrite.from_user == self.user.id).get()
            give = money_write.cent_amount < 0
            to_user = money_write.to_user
            a = f"<@{self.user.id}>"
            b = f"<@{to_user.id}>"
            if give ^ (self.group.type == "money_give"):
                a, b = b, a
            embed.description += f"### {format_euro_sign(money_write.cent_amount)}\n"
            embed.description += f"{a}`--{"owes" if self.group.type == "credit" else "payed"}-->`{b}"
        else:
            # new field where each line is the arrow + description, cannot be very long as a result :(
            ...
        embed.add_field(name="creator:", value=f"<@{self.group.created_by}>", inline=True)
        embed.add_field(name="date:", value=mention_datetime(self.group.created_at, "f"), inline=True)
        embed.add_field(name="unique id:", value=f"```js\n{self.unique_id}\n```", inline=True)

        if self.group.description or self.group.description_edited:
            embed.add_field(name=f"description{" (edited)" if self.group.description_edited else ""}:",
                            value=f">>> {self.group.description}" if self.group.description else f"`deleted` {trash_can_emoji}",
                            inline=False)
        if self.group.description:
            yield Button(label="delete description", style=ButtonStyle.red, _callable=self.delete_description, row=2)
            yield Button(label="edit description", style=ButtonStyle.blurple, _callable=self.change_description, row=2)
        else:
            yield Button(label="add description", style=ButtonStyle.green, _callable=self.change_description, row=2)
        if self.group.image_url:
            embed.add_field(name=f"image{" (edited)" if self.group.image_url_edited else ""}:",
                            value="to edit image use: " + mention_slash_command("edit_image"),
                            inline=False)
            embed.set_image(url=self.group.image_url)
            yield Button(label="delete picture", style=ButtonStyle.red, _callable=self.delete_picture, row=3)
        else:
            embed.add_field(name="image:", value="to add image use: " + mention_slash_command("add_image"),
                            inline=False)
        embed.set_footer(icon_url=help_icon_url, text=f"positive: you owe this person,  "
                                                      f"negative: this person owes you")
        if not deleted:
            if self.participant.can_delete:
                yield Button(label=f"delete this {self.name}", row=4, style=ButtonStyle.red, _callable=self.delete)
            elif self.participant.can_request_deletion:
                yield Button(label=f"request deleting this {self.name}", row=4, style=ButtonStyle.red,
                             _callable=self.request_delete)
        yield embed

    def clean_up(self):
        image_listener.remove_listener(self.user.id)


class DescriptionModal(discord.ui.Modal):

    def __init__(self, debt_command_view: DebtView, old_description: str | None):
        super().__init__(title="change description")
        self.debt_command_view = debt_command_view
        self.old_description = old_description

        self.name = discord.ui.TextInput(
            label='description',
            placeholder='description for the money...',
            default=self.old_description,
            style=discord.TextStyle.long,
            max_length=1000
        )
        self.add_item(self.name)

    async def on_submit(self, interaction: discord.Interaction):
        await self.debt_command_view.change_description_confirm(interaction, self.name.value)


class DeleteConfirm(discord.ui.View):
    def __init__(self, uid: str, name: str, view: DebtView, ephemeral, subgroups, user: User):
        super().__init__()
        self.uid = uid
        self.name = name
        self.view = view
        self.ephemeral = ephemeral
        self.subgroups = subgroups
        self.user = user

    @discord.ui.button(label='delete', style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.view.delete_confirmed()
        if is_group_id(self.uid):
            for subgroup in self.subgroups:
                subgroup.deleted_at = datetime.datetime.now()
            MoneyWriteSubGroup.bulk_update(self.subgroups, fields=["deleted_at"])
        else:
            raise "not implemented"
        await run_application(interaction, DebtView(unique_id=self.uid, ephemeral=self.ephemeral, user=self.user),
                              is_initial=False)
        self.stop()

    @discord.ui.button(label='cancel', style=discord.ButtonStyle.blurple)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.delete_original_response()
        self.stop()


