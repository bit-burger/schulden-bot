from typing import Literal

from discord import app_commands

from .utils.database_utils import *
from .utils.application_view import *
from .utils.discord_utils import *
from .utils.formatting import *
from config import tree, help_icon_url, trash_can_emoji
from database.calculate_debt import user_history_page_count, user_history, total_balance_with_user
from database.permissions import can_send

import datetime

page_size = 5


@tree.command(name='history', description="history of debt with single person",
              guild=discord.Object(id=1201588191094906890))
@app_commands.describe(show="if this slash command should be viewable from outside (change default in /settings)")
@app_commands.rename(who="with")
async def history(interaction: discord.Interaction, who: discord.Member, show: Optional[Literal["yes", "no"]]):
    user = check_register(interaction)
    ephemeral = ephemeral_from_arg(user, show)
    with_user = check_register_from_id(who.id)
    if not can_send(user, with_user):
        return await send_success_embed(interaction, title="Cannot view debt with this person",
                                        description="user may have not whitelisted you")
    if not can_send(with_user, user):
        return await send_success_embed(interaction, title="Cannot view debt with this person",
                                        description="you have blocked or not whitelisted this user")
    await run_application(interaction,
                          HistoryView(user=user, member=interaction.user, with_user=with_user, ephemeral=ephemeral))


class HistoryView(UserApplicationView):

    def __init__(self, ephemeral: bool, user: User, member: discord.Member, with_user: User):
        super().__init__(user=user, ephemeral=ephemeral)
        self.newest_first = True
        self.page = 0
        self.with_user = with_user
        self.member = member

    # todo: refresh, page back, page front, show how you can show history with user

    async def to_first_page(self, i, b):
        self.page = 0
        await self.set_state(i)

    async def one_page_back(self, i, b):
        self.page -= 1
        await self.set_state(i)

    async def one_page_forward(self, i, b):
        self.page += 1
        await self.set_state(i)

    async def to_last_page(self, i, b):
        self.page = user_history_page_count(self.user, self.with_user, page_size) - 1
        await self.set_state(i)

    async def refresh(self, i, b):
        await self.set_state(i)

    async def reverse_order(self, i, b):
        self.newest_first = not self.newest_first
        self.page = 0
        await self.set_state(i)

    def render(self) -> Iterator[str | discord.Embed | ui.Item]:
        page_count = user_history_page_count(self.user, self.with_user, page_size)
        is_last_page = self.page == page_count - 1
        is_first_page = self.page == 0
        page_data = [*user_history(self.user, self.with_user, newest_first=self.newest_first, page_size=page_size,
                                   page=self.page,
                                   desc_max_length=20)]
        balance = total_balance_with_user(self.user, with_other=self.with_user)
        embed = discord.Embed()
        embed.set_author(name=f"{self.member.name}", icon_url=self.member.display_avatar.url)
        if page_count == 0:
            if self.ephemeral:
                embed.description = "You have not registered any debt/repayment so far with this user"
            else:
                embed.description = f"<@{self.user.id}> has not registered any debt/repayment so far with <@{self.with_user.id}>"
            yield embed
            return
        max_len = 0
        for data in page_data:
            length = len(format_euro(abs(data['cent_amount'])))
            max_len = max(max_len, length)
        embed.description = f"## Your debt and repayment history with <@{self.with_user.id}>\n"
        embed.description += f"### total balance: {format_euro_sign(balance)}\n"
        embed.description += f"### view, edit, delete: {mention_slash_command("view")}` [unique id]`"

        creators = ""
        descriptions = ""
        amounts = ""
        for data in page_data:
            deleted = data["is_deleted"]
            id = f"`{data["id"]}    `"
            if data["sub_id"]:
                id = f"`{data["id"]}({data["sub_id"]}) `"
            amount = sign_emoji(data["cent_amount"], deleted=deleted) + "`" + pad_to_len(format_euro(abs(data["cent_amount"])),
                                                                        max_len + 2) + "`"
            description = (data["description"] or "-")
            creator = f"<@{data["created_by"]}>  "
            created_at: datetime.datetime = data["created_at"]
            timestamp = int(created_at.timestamp())
            if created_at.date() == datetime.datetime.today().date():
                time = f"{mention_timestamp(timestamp, "t")}"
            else:
                time = f"{mention_timestamp(timestamp, "d")}"

            match data["type"]:
                case "group_debt":
                    type_ = "👥"
                case "money_give":
                    type_ = "💶"
                case _:
                    type_ = "📒"  # 📒🗄📁🗂️📝💾
            amounts += amount + time + (trash_can_emoji if deleted else "") + "\n"
            descriptions += type_ + " " + description + "\n"
            creators += id + creator + "\n"

        embed.add_field(name="amount" + " " * (6 + max_len) + "date", value=amounts)
        embed.add_field(name="description", value=descriptions)
        embed.add_field(name="unique id     creator", value=creators)

        embed.set_footer(icon_url=help_icon_url,
                         text=f"positive: you owe this person,  "
                              f"negative: this person owes you, "
                              f"trashcan: was deleted\n"
                              f"📒: amount was lent,  "
                              f"👥: amount was lent to multiple people,  "
                              f"💶: amount was payed"
                         )
        yield Button(label="⏪", disabled=is_first_page, _callable=self.to_first_page)
        yield Button(label="◀️", disabled=is_first_page, _callable=self.one_page_back)
        yield Button(label=f"{self.page + 1}/{page_count}", disabled=True, style=discord.ButtonStyle.grey)
        yield Button(label="▶️", disabled=is_last_page, _callable=self.one_page_forward)
        yield Button(label="⏩", disabled=is_last_page, _callable=self.to_last_page)
        yield Button(label="↺ refresh", style=discord.ButtonStyle.green, _callable=self.refresh)
        yield Button(label="↑↓ reverse order", style=discord.ButtonStyle.green, _callable=self.reverse_order)
        yield embed
