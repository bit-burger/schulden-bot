import asyncio
import random
import string
from functools import partial
from typing import Literal

from discord import Embed, app_commands, Member, ButtonStyle, Interaction

from .utils.application_view import *
from .utils.database_utils import *
from .utils.formatting import *
from .utils.discord_utils import *
from config import tree, help_icon_url
from database.database_schema import *
from database.permissions import can_send
from .attachment import image_listener
from .view_entry import DebtView, _interaction_message_cache


# all commands:
# debt // general, has to be given as parameter in slash command
# debt owe
# debt [opposite of owe]

# should be possible to switch which direction and if money is owed or payed

# idea: put direction and type into same field, and just two buttons
# [Change to: @b--owe-->@a]   [Change to: @a--payed-->@b]

async def simple_money_write(i: discord.Interaction, amount: Optional[str], who: discord.Member,
                             description: Optional[str],
                             image: Optional[discord.Attachment], yourself_err, bot_err, non_wl_err, non_self_wl_err,
                             give, type):
    if image and not attachment_is_image(image):
        return await send_error_embed(i, title="parameter 'image' only supports images or pdfs")
    if len(description or "") > 1000:
        return await send_error_embed(i, title="Description too long",
                                      description=f"should contain max 1000 characters, "
                                                  f"but contains {len(description)} characters")
    cent_amount = str_to_euro_cent(amount) if amount else None
    if who.id == i.user.id:
        return await send_error_embed(i, title=yourself_err)
    if who.bot:
        return await send_error_embed(i, title=bot_err)
    # if not cent_amount:
    #     return await send_error_embed(i, title="Not a valid amount",
    #                                   description=f"'**{amount}**' is not a positive sum of euro and euro cent")
    user = check_register(i)
    to_user = check_register_from_id(who.id)
    if cent_amount:
        max_interaction_error_str = max_interaction_error(user, to_user, cent_amount)
        if max_interaction_error_str:
            return await send_error_embed(i, title="Amount to high",
                                          description=max_interaction_error_str)
    if not can_send(user, to_user):
        return await send_success_embed(i, title=non_wl_err,
                                        description="user may have not whitelisted you")
    if not can_send(to_user, user):
        return await send_success_embed(i, title=non_self_wl_err,
                                        description="you have blocked or not whitelisted this user")
    url = None
    if image is not None:
        url = image.url
    app = DebtCommandView(
        user=user,
        member=i.user,
        to_user=to_user,
        to_member=who,
        description=description,
        raw_cent_amount=amount,
        cent_amount=cent_amount,
        url=url,
        give=give,
        type=type
    )
    await run_application(i, app)


wl_you_str = "as they have not whitelisted you"
wl_them_str = "as you have not whitelisted them"


@tree.command(name='owe', description="register when you owe someone",
              guild=discord.Object(config.test_guild_id) if config.test_guild_id else None)
@app_commands.describe(
    amount="the amount of money that you owe",
    who="Who you owe the money",
    description="why you owe this money",
    image="an attachment for the debt (could be a photo of a receipt)",
)
async def owe(i: discord.Interaction, amount: Optional[str], who: discord.Member, description: Optional[str],
              image: Optional[discord.Attachment]):
    await simple_money_write(
        i, amount, who, description, image, "You can't owe yourself!", "You can't owe a bot!",
        "Cannot register owing this user money, " + wl_you_str,
        "Cannot register owing this user money, " + wl_them_str, False, "credit"
    )


@tree.context_menu(name="owe (you owe them money)",
                   guild=discord.Object(config.test_guild_id) if config.test_guild_id else None)
async def owe_context(i: discord.Interaction, who: discord.Member):
    await simple_money_write(
        i, None, who, None, None, "You can't owe yourself!", "You can't owe a bot!",
        "Cannot register owing this user money, " + wl_you_str,
        "Cannot register owing this user money, " + wl_them_str, False, "credit"
    )


@tree.command(name='pay', description="register when you pay/give someone money",
              guild=discord.Object(config.test_guild_id) if config.test_guild_id else None)
@app_commands.describe(
    amount="the amount of money that you have given",
    who="Who you gave the money",
    description="why you gave this money",
    image="an attachment showing you gave this money (could be a photo of a receipt)",
)
async def pay(i: discord.Interaction, amount: Optional[str], who: discord.Member, description: Optional[str],
              image: Optional[discord.Attachment]):
    await simple_money_write(
        i, amount, who, description, image, "You can't register giving yourself money!",
        "You can't register giving a bot money!",
        "Cannot register giving this user money, " + wl_you_str,
        "Cannot register giving this user money, " + wl_them_str, True, "money_give"
    )


@tree.context_menu(name="pay (you gave them money)",
                   guild=discord.Object(config.test_guild_id) if config.test_guild_id else None)
async def pay_context(i: discord.Interaction, who: discord.Member):
    await simple_money_write(
        i, None, who, None, None, "You can't register giving yourself money!",
        "You can't register giving a bot money!",
        "Cannot register giving this user money, " + wl_you_str,
        "Cannot register giving this user money, " + wl_them_str, True, "money_give"
    )


@tree.command(name='debt', description="register when someone owes you money",
              guild=discord.Object(config.test_guild_id) if config.test_guild_id else None)
@app_commands.describe(
    amount="the amount of money that this user owes you",
    who="Why they owe you this money",
    description="why they you owe this money",
    image="an attachment for the debt (could be a photo of a receipt)",
)
async def debt(i: discord.Interaction, amount: Optional[str], who: discord.Member, description: Optional[str],
               image: Optional[discord.Attachment]):
    await simple_money_write(
        i, amount, who, description, image, "You can't owe yourself!", "You can't owe a bot!",
        "Cannot register debt from this user, " + wl_you_str,
        "Cannot register debt from this user, " + wl_them_str, True, "credit"
    )


@tree.context_menu(name="debt (they owe you money)",
                   guild=discord.Object(config.test_guild_id) if config.test_guild_id else None)
async def debt_context(i: discord.Interaction, who: discord.Member):
    await simple_money_write(
        i, None, who, None, None, "You can't owe yourself!", "You can't owe a bot!",
        "Cannot register debt from this user, " + wl_you_str,
        "Cannot register debt from this user, " + wl_them_str, True, "credit"
    )


@tree.command(name='payed-off', description="register when you accept money from someone",
              guild=discord.Object(config.test_guild_id) if config.test_guild_id else None)
@app_commands.describe(
    amount="the amount of money that you have accepted",
    who="Who gave you the money",
    description="why they gave you this money",
    image="an attachment showing they gave you the money (could be a photo of a receipt)",
)
async def payed_off(i: discord.Interaction, amount: Optional[str], who: discord.Member, description: Optional[str],
                    image: Optional[discord.Attachment]):
    await simple_money_write(
        i, amount, who, description, image, "You can't owe yourself!", "You can't owe a bot!",
        "Cannot register accepting money from this user, " + wl_you_str,
        "Cannot register accepting money from this user, " + wl_them_str, False, "money_give"
    )


@tree.context_menu(name="payed-off (they gave you money)",
                   guild=discord.Object(config.test_guild_id) if config.test_guild_id else None)
async def payed_off(i: discord.Interaction, who: discord.Member):
    await simple_money_write(
        i, None, who, None, None, "You can't owe yourself!", "You can't owe a bot!",
        "Cannot register accepting money from this user, " + wl_you_str,
        "Cannot register accepting money from this user, " + wl_them_str, False, "money_give"
    )


class DebtCommandView(UserApplicationView):

    async def interaction_check(self, interaction: Interaction, /) -> bool:
        return interaction.user.id == self.user.id

    def __init__(self, user: User, member: Member, to_user: User, to_member: Member,
                 description: str | None, raw_cent_amount: Optional[str], cent_amount: Optional[int],
                 url: str | None, give: bool,
                 type: Literal["money_give", "credit"]):
        super().__init__(user=user, ephemeral=ephemeral_from_arg(user, None))
        self.state = "confirmation"
        self.member = member
        self.to_user = to_user
        self.to_member = to_member
        self.description = description
        self.raw_cent_amount = raw_cent_amount
        self.cent_amount = cent_amount
        self.url = url
        self.give = give
        self.type = type
        self.error = None
        if not cent_amount:
            if raw_cent_amount:
                self.error = f'"{raw_cent_amount}" is not a valid amount of money'
            else:
                self.error = "no valid amount of money given"
        self.timestamp = None
        self.unique_identifier = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        image_listener.add_listener(self.user.id, self)

    async def event(self, event):
        interaction = event[0]
        self.url = event[1]
        await asyncio.gather(
            run_application(interaction, DebtCommandView(
                user=self.user,
                member=self.member,
                to_user=self.to_user,
                to_member=self.to_member,
                description=self.description,
                raw_cent_amount=self.raw_cent_amount,
                cent_amount=self.cent_amount,
                url=self.url,
                give=self.give,
                type=self.type
            )),
            self.last_interaction.delete_original_response()
        )

    def render(self):
        match self.state:
            case "confirmation":
                yield from self.render_confirmation()
            case "cancelled":
                yield Embed(title="Canceled slash command")

    async def confirm(self, i, b):
        group = MoneyWriteGroup.create(id=self.unique_identifier, description=self.description, created_by=self.user,
                                       type=self.type,
                                       image_url=self.url)
        sub_group = MoneyWriteSubGroup.create(group=group)
        self_participant = MoneyWriteGroupParticipant.create(group=group, participant=self.user,
                                                             can_delete=self.give,
                                                             can_request_deletion=True)
        MoneyWriteGroupParticipant.create(group=group, participant=self.to_user, can_delete=not self.give,
                                          can_request_deletion=True)
        cent_amount = self.cent_amount
        if self.give:
            cent_amount *= -1
        rows = [{'sub_group': sub_group, 'cent_amount': cent_amount, 'from_user': self.user, 'to_user': self.to_user}, {
            'sub_group': sub_group, 'cent_amount': -cent_amount, 'from_user': self.to_user, 'to_user': self.user}]
        MoneyWrite.insert_many(rows).execute()

        self.timestamp = group.created_at

        self.clean_up()
        await DebtView.run_system_on_interaction(i, (self.unique_identifier, self.user.id, True), is_initial=False)

        message = await self.last_interaction.original_response()
        _interaction_message_cache[message.id] = message
        ViewDebtEntryMessages.create(message_id=message.id,
                                     channel_id=message.channel.id,
                                     debt_entry=self.unique_identifier,
                                     user_id=self.user.id)

    async def cancel(self, i, b):
        self.stop()
        self.state = "cancelled"
        await self.set_state(i)

    async def toggle_give(self, i, b):
        self.give = not self.give
        await self.set_state(i)

    async def toggle_type(self, i, b):
        self.type = "money_give" if self.type == "credit" else "credit"
        await self.set_state(i)

    async def change_amount(self, i, b):
        await i.response.send_modal(AmountModal(self))

    async def change_amount_confirm(self, i, raw_amount):
        amount = str_to_euro_cent(raw_amount)
        if amount is None:
            self.error = f'"amount" could not be changed as "{raw_amount}" is not a valid amount of money'
            await self.set_state(i)
            return
        if amount == 0:
            self.error = "amount could not be changed as amount has to be positive"
            await self.set_state(i)
            return
        max_interaction_error_str = max_interaction_error(self.user, self.to_user, amount, human_readable_format=True)
        if max_interaction_error_str:
            self.error = max_interaction_error_str
            await self.set_state(i)
            return
        self.raw_cent_amount = None
        self.cent_amount = amount
        await self.set_state(i)

    async def change_amount_by(self, by: int, i, b):
        self.cent_amount += by
        self.raw_cent_amount = None
        await self.set_state(i)

    async def change_description(self, i, b):
        await i.response.send_modal(DescriptionModal(self, self.description))

    async def change_description_confirm(self, i, description):
        self.description = description
        await self.set_state(i)

    async def delete_description(self, i, b):
        self.description = None
        await self.set_state(i)

    async def delete_picture(self, i, b):
        self.url = None
        await self.set_state(i)

    def render_confirmation(self):
        embed = Embed(title="Confirmation",
                      description="Please fill out the field `amount` before proceeding" if not self.cent_amount else self.confirmation_text() + " After confirming you cannot change the **amount**")
        yield Button(label="Confirm", style=ButtonStyle.green, _callable=self.confirm, disabled=not self.cent_amount,
                     row=4)
        yield Button(label="Cancel", style=ButtonStyle.red, _callable=self.cancel, row=4)
        embed.add_field(name="direction", value=self.direction_text(), inline=False)
        if self.give:
            yield Button(label="Change to: " + self.toggled_readable_direction_text(),
                         _callable=self.toggle_give,
                         row=0)
        else:
            yield Button(label="Change to: " + self.toggled_readable_direction_text(),
                         _callable=self.toggle_give,
                         row=0)
        embed.add_field(name="type", value="debt" if self.type == "credit" else "payment", inline=False)
        if self.type == "credit":
            yield Button(label="mark as 'payment' instead of 'debt'",
                         _callable=self.toggle_type,
                         row=0)
        else:
            yield Button(label="mark as 'debt' instead of 'payment'",
                         _callable=self.toggle_type,
                         row=0)
        if not self.cent_amount:
            embed.add_field(name="amount", value=f"`no valid amount given yet`")
        elif self.raw_cent_amount:
            embed.add_field(name="amount", value=f"`{self.raw_cent_amount} = {format_euro(self.cent_amount)}`")
        else:
            embed.add_field(name="amount", value=f"`{format_euro(self.cent_amount)}`")
        yield Button(label="set amount" if not self.cent_amount else "edit amount", _callable=self.change_amount, row=1)
        yield Button(label="+1€", _callable=partial(self.change_amount_by, 100), disabled=not self.cent_amount, row=1)
        yield Button(label="-1€", disabled=not self.cent_amount or self.cent_amount <= 100,
                     _callable=partial(self.change_amount_by, -100), row=1)
        yield Button(label="+0.20€", _callable=partial(self.change_amount_by, 20), disabled=not self.cent_amount, row=1)
        yield Button(label="-0.20€", disabled=not self.cent_amount or self.cent_amount <= 20,
                     _callable=partial(self.change_amount_by, -20), row=1)
        if self.description:
            embed.add_field(name="description", value=self.description, inline=False)
            yield Button(label="delete description", emoji=config.trash_can_emoji_p, _callable=self.delete_description,
                         row=3)
            yield Button(label="edit description", _callable=self.change_description, row=2)
        else:
            yield Button(label="add description", _callable=self.change_description, row=2)
        if self.url:
            embed.add_field(name="image:", value="to edit image use: " + mention_slash_command("edit_image"),
                            inline=False)
            embed.set_image(url=self.url)
            yield Button(label="delete picture", emoji=config.trash_can_emoji_p, style=ButtonStyle.grey,
                         _callable=self.delete_picture, row=3)
        else:
            embed.add_field(name="image:", value="to add image use: " + mention_slash_command("add_image"),
                            inline=False)
        if self.error:
            embed.set_footer(icon_url=help_icon_url, text=self.error)
        yield embed

    def direction_text(self):
        a = f"<@{self.user.id}>"
        b = f"<@{self.to_user.id}>"
        if self.give ^ (self.type == "money_give"):
            a, b = b, a
        return f"{a}`--{"owes" if self.type == "credit" else "payed"}-->`{b}"

    def toggled_readable_direction_text(self):
        a = f"@{self.to_member.display_name}"
        b = f"@{self.member.display_name}"
        if self.give ^ (self.type == "money_give"):
            a, b = b, a
        return f"{a}--{"owes" if self.type == "credit" else "payed"}-->{b}"

    def confirmation_text(self):
        m = f"<@{self.to_user.id}>"
        a = f"**{format_euro(self.cent_amount)}**"
        if self.give and self.type == "money_give":
            return f"Do you want to register that you gave {a} to {m}?"
        if self.type == "money_give":
            return f"Do you want to register that {a} gave you {m}?"
        if not self.give:
            return f"Do you want to register that you owe {m} {a}?"
        return f"Do you want to register that {m} owes you {a}?"

    def clean_up(self):
        image_listener.remove_listener(self.user.id)


class DescriptionModal(discord.ui.Modal):

    def __init__(self, debt_command_view: DebtCommandView, old_description: str | None):
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


class AmountModal(discord.ui.Modal):

    def __init__(self, debt_command_view: DebtCommandView):
        super().__init__(title="change amount")
        self.debt_command_view = debt_command_view

        self.name = discord.ui.TextInput(
            label='amount',
            placeholder='amount of money...',
            max_length=30
        )
        self.add_item(self.name)

    async def on_submit(self, interaction: discord.Interaction):
        await self.debt_command_view.change_amount_confirm(interaction, self.name.value)
