import asyncio
from typing import Iterable, Iterator

import discord
from discord import app_commands, ButtonStyle, ui

from .attachment import image_listener
from .example_persistent import ExamplePersistent
from .utils.application_view import ApplicationView, UserApplicationView, run_application
import commands.utils.application_view as application_view
from .utils.formatting import *
from commands.utils.database_utils import *
from commands.utils.discord_utils import send_error_embed
from config import tree, trash_can_emoji, help_icon_url, client
from database.groups import *
from .utils.persistent_view import ButtonSystem, Button

_interaction_message_cache = dict()


# TODO: _ephermeral_interaction_cache = dict()


async def edit_view_debt_interactions(unique_id, user_id):
    for entry in ViewDebtEntryMessages.select().where(ViewDebtEntryMessages.debt_entry == unique_id):
        try:
            if entry.message_id in _interaction_message_cache:
                message = _interaction_message_cache[entry.message_id]
            else:
                channel = await client.fetch_channel(entry.channel_id)
                message = await channel.fetch_message(entry.message_id)
            await DebtView.run_system_on_message(message, (
                entry.debt_entry, entry.user_id, entry.is_deletion_request, entry.is_deletion_request))
        except:
            ...


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
    # await asyncio.gather(
    #     interaction.response.defer(),
    #     interaction.delete_original_response(),
    #     DebtView.run_system_on_channel(interaction.channel, (unique_id, user.id)),
    # )
    await DebtView.run_system_on_interaction(interaction, (unique_id, user.id, ephemeral), ephemeral=ephemeral),
    if not ephemeral:
        message = await interaction.original_response()
        _interaction_message_cache[message.id] = message
        ViewDebtEntryMessages.create(message_id=message.id, channel_id=message.channel.id, debt_entry=unique_id,
                                     user_id=user.id)


class DebtView(ButtonSystem, name="dv"):
    def __init__(self, data, ephemeral, button_name, button, ac_interaction=None):
        super().__init__(data, ephemeral=ephemeral, button_name=button_name, button=button,
                         ac_interaction=ac_interaction)
        user = User.get_by_id(self.user_id)
        self.group = get_group(self.unique_id, user)
        self.sub_groups = [*self.group.sub_groups]
        self.participant = get_participant(self.unique_id, user)
        if self.group.type == "credit":
            self.name = "debt entry"
        elif self.group.type == "group_credit":
            self.name = "group debt entry"
        elif self.group.type == "money_give":
            self.name = "payment entry"
        else:
            raise "embed type does not exist"

    @property
    def unique_id(self):
        return self.data[0]

    @property
    def user_id(self):
        return self.data[1]

    @property
    def hidden(self):
        return self.data[2]

    @property
    def is_deletion_request(self):
        if self.deleted or len(self.data) < 4:
            return False
        return self.data[3]

    @property
    def deleted(self):
        return all(map(lambda s_g: s_g.deleted_at is not None, self.sub_groups))

    async def check_edit(self):
        user_id = self.current_interaction.user.id
        participant = get_participant(self.unique_id, User.get_by_id(user_id))
        return participant is not None

    async def edit(self):
        user_id = self.current_interaction.user.id
        participant = get_participant(self.unique_id, User.get_by_id(user_id))
        await run_application(self.current_interaction,
                              DebtEdit(self.group, self.sub_groups, participant, self.unique_id, self.name,
                                       user_id=user_id, hidden=self.hidden, ac_interaction=self.current_interaction),
                              is_initial=not self.hidden)

    def render(self) -> Iterable[Button | discord.Embed | str]:
        if is_group_id(self.unique_id):
            yield from self.render_group()
        else:
            yield from self.render_sub_group()

    def render_sub_group(self):
        # yield button that allows to view main group
        ...

    async def ignore(self):
        await self.current_interaction.response.defer()
        await self.current_interaction.delete_original_response()

    async def delete(self):
        if is_group_id(self.unique_id):
            for subgroup in self.sub_groups:
                subgroup.deleted_at = datetime.datetime.now()
            MoneyWriteSubGroup.bulk_update(self.sub_groups, fields=["deleted_at"])
        else:
            raise "not implemented"
        await self.set_state(data=self.data)

    def render_group(self):
        # edited = any(map(lambda s_g: s_g.edited is True, self.sub_groups)) or self.group.description_edited
        embed = discord.Embed(color=0xFF0000 if self.deleted or self.is_deletion_request else None)

        if self.is_deletion_request:
            embed.description = "### Do you want to delete this " + self.name + "?\n"
        else:
            embed.description = "### " + self.name

            if self.deleted:
                embed.description += f" {trash_can_emoji} (deleted)"
            #     embed.description += f" ✏️ (edited)"
            embed.description += "\n"

        if self.group.type == "money_give" or self.group.type == "credit":
            sub_group = self.sub_groups[0]
            money_write = sub_group.money_writes.where(MoneyWrite.from_user == self.user_id).get()
            give = money_write.cent_amount < 0
            to_user = money_write.to_user
            a = f"<@{self.user_id}>"
            b = f"<@{to_user.id}>"
            if give ^ (self.group.type == "money_give"):
                a, b = b, a
            embed.description += f"{a}`--{"owes" if self.group.type == "credit" else "payed"}-->`{b}`{format_euro(abs(money_write.cent_amount))}`"
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
        if self.group.image_url:
            embed.add_field(name=f"image{" (edited)" if self.group.image_url_edited else ""}:",
                            value="",
                            inline=False)
            embed.set_image(url=self.group.image_url)
        yield embed
        if self.is_deletion_request:
            yield Button(label="delete", button_name="delete", style=ButtonStyle.red)
            yield Button(label="ignore", button_name="ignore", style=ButtonStyle.grey)
        if not self.deleted:
            yield Button(label="edit" if self.is_deletion_request else "edit/delete", button_name="edit",
                         style=ButtonStyle.blurple)
        # yield button that gives message with selection menu to view under group


# use select to
class DebtEdit(ApplicationView):
    def __init__(self, group, sub_groups, participant, uid, name, user_id, hidden, ac_interaction):
        super().__init__()
        self.group = group
        self.sub_groups = sub_groups
        self.participant = participant
        self.uid = uid
        self.name = name
        self.edited = False
        self.user_id = user_id
        self.saved = False
        self.deleted = False
        self.hidden = hidden
        self.ac_interaction = ac_interaction

        image_listener.add_listener(self.user_id, self)

    async def change_description(self, i, b):
        await i.response.send_modal(DescriptionModal(self, self.group.description))

    async def change_description_confirm(self, interaction, description: str):
        self.group.description = description
        self.group.description_edited = True
        self.group.save()
        self.edited = True
        await self.set_state(interaction)

    async def delete_description(self, i, b):
        self.group.description = None
        self.group.description_edited = True
        self.group.save()
        self.edited = True
        await self.set_state(i)

    async def delete_picture(self, i, b):
        self.group.image_url = None
        self.group.image_url_edited = True
        self.edited = True
        # self.group.save()
        await self.set_state(i)

    async def delete(self, i: discord.Interaction, b):
        await i.response.send_message(
            embed=discord.Embed(title="confirm", description=f"do you really want to delete this {self.name}?",
                                color=0xFF0000),
            view=DeleteConfirm(name=self.name,
                               subgroups=self.sub_groups, edit_interaction=self.ac_interaction, uid=self.uid,
                               debt_edit=self,
                               user_id=self.user_id, hidden=self.hidden), ephemeral=True)

    async def request_delete(self, i: discord.Interaction, b):
        other_participant = self.group.participants.where(MoneyWriteGroupParticipant.participant != self.user_id).get()
        user = await config.client.fetch_user(other_participant.participant.id)
        dm = user.dm_channel
        if not dm:
            dm = await user.create_dm()
        try:
            message = await DebtView.run_system_on_channel(dm, (self.uid, i.user.id, True, True))
            ViewDebtEntryMessages.create(message_id=message.id, channel_id=message.channel.id, debt_entry=self.uid,
                                         user_id=user.id, is_deletion_request=True)
            request_success = True
        except:
            request_success = False
        if request_success:
            await i.response.edit_message(embed=discord.Embed(title="Successfully sent deletion request!",
                                                              description=f"The bot successfully sent a dm message to <@{user.id}> for the deletion of the debt entry with id `{self.uid}`",
                                                              color=0x00FF00), view=None)
        else:
            await i.response.send_message(embed=discord.Embed(title="Could not send deletion request!",
                                                              description=f"The bot failed sending a dm message to <@{user.id}>, perhaps this user has not allowed the ",
                                                              color=0xFF0000), ephemeral=True)

    async def save(self, i, b):
        self.edited = False
        self.group.save()
        if self.hidden:
            await i.response.send_message(
                embed=discord.Embed(title="Saved successfully",
                                    description="your changes have been saved successfully",
                                    color=0x00FF00))
            await DebtView.run_system_on_interaction_edit(i, (self.uid, self.user_id, self.hidden)),
            await edit_view_debt_interactions(self.uid, self.user_id)
        else:
            self.saved = True
            await self.set_state(i)
            await edit_view_debt_interactions(self.uid, self.user_id)

    async def cancel(self, i, b):
        await i.response.defer()
        await i.delete_original_response()
        self.clean_up()

    async def event(self, event):
        interaction = event[0]
        image_listener.add_listener(self.user_id, self)
        self.group.image_url = event[1]
        self.group.image_url_edited = True
        self.edited = True
        self.clean_up()
        await asyncio.gather(
            run_application(interaction, self),
            self.last_interaction.delete_original_response()
        )

    def render(self) -> Iterator[str | discord.Embed | ui.Item]:
        if self.saved:
            yield discord.Embed(title="Saved successfully", description="your changes have been saved successfully",
                                color=0x00FF00)
            return
        # if self.deleted:
        #     return [discord.Embed(title="Deleted successfully", description="the debt entry has been successfully deleted", color=0xFF0000)]
        deleted = all(map(lambda s_g: s_g.deleted_at is not None, self.sub_groups))
        embed = discord.Embed(color=discord.colour.Color.blurple())
        if self.group.type == "money_give" or self.group.type == "credit":
            sub_group = self.sub_groups[0]
            money_write = sub_group.money_writes.where(MoneyWrite.from_user == self.user_id).get()
            give = money_write.cent_amount < 0
            to_user = money_write.to_user
            a = f"<@{self.user_id}>"
            b = f"<@{to_user.id}>"
            if give ^ (self.group.type == "money_give"):
                a, b = b, a
            embed.description = f"### editing debt entry ✏️:\n"
            # embed.description += f"#### {format_euro_sign(money_write.cent_amount)}\n"
            # embed.description += f"{a}`--{"owes" if self.group.type == "credit" else "payed"}-->`{b}"
            embed.description += f"{a}`--{"owes" if self.group.type == "credit" else "payed"}-->`{b}`{format_euro(abs(money_write.cent_amount))}`"
        else:
            # new field where each line is the arrow + description, cannot be very long as a result :(
            ...

        embed.add_field(name="creator:", value=f"<@{self.group.created_by}>", inline=True)
        embed.add_field(name="date:", value=mention_datetime(self.group.created_at, "f"), inline=True)
        embed.add_field(name="unique id:", value=f"```js\n{self.uid}\n```", inline=True)

        if self.group.description or self.group.description_edited:
            embed.add_field(name=f"description{" (edited)" if self.group.description_edited else ""}:",
                            value=f">>> {self.group.description}" if self.group.description else f"`deleted` {trash_can_emoji}",
                            inline=False)

        if self.group.description:
            yield application_view.Button(label="delete description",
                                          _callable=self.delete_description,
                                          row=1)
            yield application_view.Button(label="edit description",
                                          _callable=self.change_description,
                                          row=1)
        else:
            yield application_view.Button(label="add description",
                                          _callable=self.change_description, row=1)
        if self.group.image_url:
            embed.add_field(name=f"image{" (edited)" if self.group.image_url_edited else ""}:",
                            value="to edit image use: " + mention_slash_command("edit_image"),
                            inline=False)
            embed.set_image(url=self.group.image_url)
            yield application_view.Button(label="delete picture", _callable=self.delete_picture,
                                          row=1)
        else:
            embed.add_field(name="image:", value="to add image use: " + mention_slash_command("add_image"),
                            inline=False)
        yield application_view.Button(label="Save changes", _callable=self.save, disabled=not self.edited, row=3)
        yield application_view.Button(label="Cancel", _callable=self.cancel, style=ButtonStyle.red, row=3)
        if self.participant.can_delete:
            yield application_view.Button(label=f"delete this {self.name}", row=4, style=ButtonStyle.red,
                                          _callable=self.delete)
        elif self.participant.can_request_deletion:
            yield application_view.Button(label=f"request deleting this {self.name}", row=4, style=ButtonStyle.red,
                                          _callable=self.request_delete)
        yield embed

    def on_timeout(self) -> None:
        self.clean_up()

    def clean_up(self):
        image_listener.remove_listener(self.user_id)


class DeleteConfirm(discord.ui.View):
    def __init__(self, uid: str, name: str, subgroups, edit_interaction, debt_edit: DebtEdit, user_id, hidden):
        super().__init__()
        self.uid = uid
        self.name = name
        self.subgroups = subgroups
        self.edit_interaction = edit_interaction
        self.debt_edit = debt_edit
        self.user_id = user_id
        self.hidden = hidden

    @discord.ui.button(label='delete', style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_group_id(self.uid):
            for subgroup in self.subgroups:
                subgroup.deleted_at = datetime.datetime.now()
            MoneyWriteSubGroup.bulk_update(self.subgroups, fields=["deleted_at"])
        else:
            raise "not implemented"
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.debt_edit.clean_up()
        self.stop()
        if self.hidden:
            # on stop
            await DebtView.run_system_on_interaction_edit(self.edit_interaction, (self.uid, self.user_id, True))
        else:
            await asyncio.gather(self.edit_interaction.delete_original_response(),
                                 edit_view_debt_interactions(self.uid, self.user_id))

    @discord.ui.button(label='cancel', style=discord.ButtonStyle.blurple)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await interaction.delete_original_response()
        self.stop()


class DescriptionModal(discord.ui.Modal):
    def __init__(self, debt_edit: DebtEdit, old_description: str | None):
        super().__init__(title="change description")
        self.debt_edit = debt_edit
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
        await self.debt_edit.change_description_confirm(interaction, self.name.value)
