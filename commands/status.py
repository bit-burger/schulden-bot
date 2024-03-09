from typing import Optional, Literal

import discord
from discord import app_commands

from database.calculate_debt import *
from .utils import *
from config import tree, plus_emoji, minus_emoji, help_icon_url

page_size = 2


@tree.command(name='status', description="status of debt with all users", guild=discord.Object(id=1201588191094906890))
@app_commands.describe(show="if this slash command should be viewable from outside (default: no)")
async def status(interaction: discord.Interaction, show: Optional[Literal["yes", "no"]]):
    ephemeral = (show != "yes")
    user = check_register(interaction)
    await run_application(interaction, StatusView(user=user, member=interaction.user, ephemeral=ephemeral))




class StatusView(ApplicationView):
    credit_first = True

    def __init__(self, ephemeral: bool, user: RegisteredUser, member: discord.Member):
        super().__init__(user=user, ephemeral=ephemeral, state=0)
        self.member = member

    # todo: refresh, page back, page front, show how you can show history with user

    async def to_first_page(self, i, b):
        await self.set_state(0, i)

    async def one_page_back(self, i, b):
        await self.set_state(self.state - 1, i)

    async def one_page_forward(self, i, b):
        await self.set_state(self.state + 1, i)

    async def to_last_page(self, i, b):
        page_count = user_balance_page_count(self.user, page_size)
        await self.set_state(page_count - 1, i)

    async def refresh(self, i, b):
        await self.update(i)

    async def reverse_order(self, i, b):
        self.credit_first = not self.credit_first
        await self.set_state(0, i)

    def render(self) -> Iterator[str | discord.Embed | ui.Item]:
        page_number = self.state + 1
        page_count = user_balance_page_count(self.user, page_size)
        is_last_page = self.state == page_count - 1
        is_first_page = self.state == 0
        page_data = [*user_balance(self.user, credit_first=self.credit_first, page_size=page_size, page=self.state)]
        credit, debt = user_credit_and_debt(self.user)
        embed = discord.Embed(description="")
        embed.set_author(name=f"{self.member.name}", icon_url=self.member.display_avatar.url)
        if page_count == 0:
            if self.ephemeral:
                embed.description = "You have not registered any debt/repayment so far"
            else:
                embed.description = f"<@{self.user.id}> has not registered any debt/repayment so far"
            yield embed
            return
        max_len = 0
        for data in page_data:
            cent_amount = data['cent_amount']
            data['money'] = format_euro(abs(cent_amount))
            data['negative'] = cent_amount < 0
            max_len = max(max_len, len(data['money']))
        for data in page_data:
            embed.description += sign_emoji(
                data['cent_amount']) + f"`{pad_to_len(data['money'], max_len)}` <@{data['user_id']}>\n"
        embed.add_field(name="sum of all debt:", value=sign_emoji(debt) + f"`{format_euro(debt)}`")
        embed.add_field(name="sum of all credit:", value=sign_emoji(-credit) + f"`{format_euro(credit)}`")
        embed.add_field(name="total sum:", value=sign_emoji(debt - credit) + f"`{format_euro(abs(debt - credit))}`")
        embed.set_footer(icon_url=help_icon_url,
                         text="positive means you owe this person (debt), negative means this person owes you (credit)")
        yield Button(label="⏪", disabled=is_first_page, _callable=self.to_first_page)
        yield Button(label="◀️", disabled=is_first_page, _callable=self.one_page_back)
        yield Button(label=f"{page_number}/{page_count}", disabled=True, style=ButtonStyle.grey)
        yield Button(label="▶️", disabled=is_last_page, _callable=self.one_page_forward)
        yield Button(label="⏩", disabled=is_last_page, _callable=self.to_last_page)
        yield Button(label="↺ refresh", style=ButtonStyle.green, _callable=self.refresh)
        yield Button(label="↑↓ reverse order", style=ButtonStyle.green, _callable=self.reverse_order)
        yield embed

