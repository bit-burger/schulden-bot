import string
import random
from typing import Optional, Literal
from functools import partial

from discord import Interaction, Embed, app_commands, Member

from .utils import *
from config import tree
from database.database_schema import MoneyWriteGroup, MoneyWrite
from database.permissions import can_send


# all commands:
# debt // general, has to be given as parameter in slash command
# debt owe
# debt [opposite of owe]

# should be possible to switch which direction and if money is owed or payed

# idea: put direction and type into same field, and just two buttons
# [Change to: @b--owe-->@a]   [Change to: @a--payed-->@b]

@tree.command(name='owe', description="when you owe someone",
              guild=discord.Object(id=1201588191094906890))
@app_commands.describe(
    amount="the amount of money that you owe",
    who="Who you owe the money",
    description="why you owe this money",
    attachment="an attachment for the debt (could be a photo of a receipt)",
)
async def owe(i: discord.Interaction, amount: str, who: discord.Member, description: Optional[str],
              attachment: Optional[discord.Attachment]):
    cent_amount = str_to_euro_cent(amount)
    if who.id == i.user.id:
        return await send_error_embed(i, title="You can't owe your self")
    if who.bot:
        return await send_error_embed(i, title="You can't owe a bot")
    if not cent_amount:
        return await send_error_embed(i, title="Not a valid amount",
                                      description=f"'**{amount}**' is not a positive sum of euro and euro cent")
    user = check_register(i)
    to_user = check_register_from_id(who.id)
    if not can_send(user, to_user):
        return await send_success_embed(i, title="Cannot owe this user money",
                                        description="user may have not whitelisted you")
    if not can_send(to_user, user):
        return await send_success_embed(i, title="Cannot owe this user money",
                                        description="you have blocked or not whitelisted this user")
    url = None
    if attachment is not None:
        url = attachment.url
    app = DebtCommandView(
        user=user,
        member=i.user,
        to_user=to_user,
        to_member=who,
        description=description,
        raw_cent_amount=amount,
        cent_amount=cent_amount,
        url=url,
        give=False,
        type="credit"
    )
    await run_application(i, app)


class DebtCommandView(ApplicationView):
    def __init__(self, user: RegisteredUser, member: Member, to_user: RegisteredUser, to_member: Member,
                 description: str | None, raw_cent_amount: str, cent_amount: int,
                 url: str | None, give: bool,
                 type: Literal["money_give", "credit"]):
        super().__init__(user=user, state="confirmation")
        self.member = member
        self.to_user = to_user
        self.to_member = to_member
        self.description = description
        self.raw_cent_amount = raw_cent_amount
        self.cent_amount = cent_amount
        self.url = url
        self.give = give
        self.type = type

    def render(self):
        match self.state:
            case "confirmation":
                yield from self.render_confirmation()
            case "finished":
                yield from self.render_finished()
            case "cancelled":
                yield Embed(title="Canceled slash command")

    async def confirm(self, i, b):
        # TODO: changeup depending on give/type
        unique_identifier = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        group = MoneyWriteGroup.create(id=unique_identifier, description=self.description, created_by=self.user,
                                       type="credit",
                                       picture=self.url)
        rows = [{'group': group, 'cent_amount': -self.cent_amount, 'from_user': self.user, 'to_user': self.to_user}, {
            'group': group, 'cent_amount': self.cent_amount, 'from_user': self.to_user, 'to_user': self.user}]
        MoneyWrite.insert_many(rows).execute()

        await self.set_state("finished", i)

    async def cancel(self, i, b):
        self.stop()
        await self.set_state("cancelled", i)

    async def toggle_give(self, i, b):
        self.give = not self.give
        await self.set_state("confirmation", i)

    async def toggle_type(self, i, b):
        self.type = "money_give" if self.type == "credit" else "credit"
        await self.set_state("confirmation", i)

    async def change_amount(self, i, b):
        self.raw_cent_amount = None
        await self.set_state("confirmation", i)

    async def change_amount_by(self, by: int, i, b):
        self.cent_amount += by
        self.raw_cent_amount = None
        await self.set_state("confirmation", i)

    async def change_description(self, i, b):
        await i.response.send_modal(DescriptionModal(self))
        await self.set_state("confirmation", i)

    async def change_description_confirm(self, i, description):
        self.description = description
        await self.set_state("confirmation", i)

    async def delete_description(self, i, b):
        self.description = None
        await self.set_state("confirmation", i)

    async def delete_picture(self, i, b):
        self.url = None
        await self.set_state("confirmation", i)

    def render_confirmation(self):
        embed = Embed(title="Confirmation", description=self.confirmation_text())
        yield Button(label="Confirm", style=ButtonStyle.green, _callable=self.confirm, row=0)
        yield Button(label="Cancel", style=ButtonStyle.red, _callable=self.cancel, row=0)
        embed.add_field(name="direction", value=self.direction_text(), inline=False)
        if self.give:
            yield Button(label="Change to: " + self.toggled_readable_direction_text(), style=ButtonStyle.blurple,
                         _callable=self.toggle_give,
                         row=1)
        else:
            yield Button(label="Change to: " + self.toggled_readable_direction_text(), style=ButtonStyle.blurple,
                         _callable=self.toggle_give,
                         row=1)
        embed.add_field(name="type", value="debt" if self.type == "credit" else "payment", inline=False)
        if self.type == "credit":
            yield Button(label="mark as 'payment' instead of 'debt'", style=ButtonStyle.blurple,
                         _callable=self.toggle_type,
                         row=1)
        else:
            yield Button(label="mark as 'debt' instead of 'payment'", style=ButtonStyle.blurple,
                         _callable=self.toggle_type,
                         row=1)
        if self.raw_cent_amount:
            embed.add_field(name="amount", value=f"`{self.raw_cent_amount} = {format_euro(self.cent_amount)}`")
        else:
            embed.add_field(name="amount", value=f"`{format_euro(self.cent_amount)}`")
        yield Button(label="edit amount", style=ButtonStyle.blurple, _callable=self.change_amount, row=2)
        yield Button(label="+1€", style=ButtonStyle.blurple, _callable=partial(self.change_amount_by, 100), row=2)
        yield Button(label="-1€", style=ButtonStyle.blurple, disabled=self.cent_amount <= 100,
                     _callable=partial(self.change_amount_by, -100), row=2)
        yield Button(label="+0.20€", style=ButtonStyle.blurple, _callable=partial(self.change_amount_by, 20), row=2)
        yield Button(label="-0.20€", style=ButtonStyle.blurple, disabled=self.cent_amount <= 20,
                     _callable=partial(self.change_amount_by, -20), row=2)
        if self.description:
            embed.add_field(name="description", value=self.description, inline=False)
            yield Button(label="delete description", style=ButtonStyle.red, _callable=self.delete_description, row=3)
            yield Button(label="edit description", style=ButtonStyle.blurple, _callable=self.change_description, row=3)
        else:
            yield Button(label="add description", style=ButtonStyle.blurple, _callable=self.change_description, row=3)
        if self.url:
            embed.add_field(name="picture", value="", inline=False)
            embed.set_image(url=self.url)
            yield Button(label="delete picture", style=ButtonStyle.blurple, _callable=self.delete_picture, row=4)
        yield embed

    def direction_text(self):
        a = f"<@{self.user.id}>"
        b = f"<@{self.to_user.id}>"
        if not self.give:
            a, b = b, a
        return f"{a}`--{"owes" if self.type == "credit" else "payed"}-->`{b}"

    def toggled_readable_direction_text(self):
        a = f"@{self.to_member.name}"
        b = f"@{self.member.name}"
        if not self.give:
            a, b = b, a
        return f"{a}--{"owes" if self.type == "credit" else "payed"}-->{b}"

    def confirmation_text(self):
        m = f"<@{self.to_user.id}>"
        a = f"**{format_euro(self.cent_amount)}**"
        if self.give and self.type == "money_give":
            return f"Do you want to confirm giving {a} {m}?"
        if self.type == "money_give":
            return f"Do you want to confirm that {a} gave you {m}?"
        if not self.give:
            return f"Do you want to confirm that you owe {m} {a}"
        return f"DO you want to confirm that {m} owes you {a}"

    def render_finished(self):
        yield "finished"


class DescriptionModal(discord.ui.Modal):

    def __init__(self, debt_command_view: DebtCommandView):
        super().__init__(title="change description")
        self.debt_command_view = debt_command_view

    name = discord.ui.TextInput(
        label='description',
        placeholder='description for the money...'
    )

    async def on_submit(self, interaction: discord.Interaction):
        await self.debt_command_view.change_description_confirm(interaction, self.name.value)

# @tree.command(name='give')
# @tree.command(name='accept')
# @tree.command(name='receive')
