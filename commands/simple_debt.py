import string
import random
from typing import Optional

from discord import app_commands

from commands.utils import *
from config import tree
from database.database_schema import MoneyWriteGroup, MoneyWrite
from database.permissions import can_send


@tree.command(name='owe', description="when you owe someone",
              guild=discord.Object(id=1201588191094906890))
@app_commands.describe(
    amount="the amount of money that you owe",
    who="Who you owe the money",
    description="why you owe this money",
    attachment="an attachment for the debt (could be a photo of a receipt)",
)
async def owe(i: discord.Interaction, amount: str, who: discord.Member, description: Optional[str],
              attachment: Optional[discord.Attachment], ):
    total_cent = str_to_euro_cent(amount)
    if who.id == i.user.id:
        return await send_error_embed(i, title="You can't owe your self")
    if who.bot:
        return await send_error_embed(i, title="You can't owe a bot")
    if not total_cent:
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
    unique_identifier = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    group = MoneyWriteGroup.create(id=unique_identifier, description=description, created_by=user, type="credit",
                                   picture=url)
    rows = [{'group': group, 'cent_amount': -total_cent, 'from_user': user, 'to_user': to_user}, {
        'group': group, 'cent_amount': total_cent, 'from_user': to_user, 'to_user': user}]
    MoneyWrite.insert_many(rows).execute()

    await send_success_embed(i, title=f"Success",
                             description=f"Successfully recorded {format_euro(total_cent)} debt with <@{to_user.id}>")

# @tree.command(name='give')
# @tree.command(name='accept')
# @tree.command(name='receive')
