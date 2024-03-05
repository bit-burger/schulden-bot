import string
from random import random
from typing import Optional

import discord
from discord import app_commands

from commands.utils import *
from config import tree
from database.database_schema import MoneyWriteGroup, MoneyWrite
from database.permissions import can_send


@tree.command(name='owe', description="when you owe someone",
              guild=discord.Object(id=1201588191094906890))
@app_commands.describe(
    euro="the amount of money that you owe in euro (will be added together with 'cent')",
    cent="the amount of money that you owe in euro cent (will be added together with 'euro')",
    who="Who you owe the money",
    description="why you owe this money",
    attachment="an attachment for the debt (could be a photo of a receipt)",
    # unique_identifier="a unique identifier for the debt"
)
@app_commands.rename(
    # unique_identifier="unique identifier"
)
async def owe(i: discord.Interaction, euro: Optional[app_commands.Range[int, 0, None]],
              cent: Optional[app_commands.Range[int, 0, None]], who: discord.Member, description: Optional[str],
              attachment: Optional[discord.Attachment], ):
    if not euro and not cent:
        return await send_success_embed(i, title="Incomplete arguments",
                                        description="'cent' and 'euro' are both zero")
    euro = euro or 0
    cent = cent or 0
    total_cent = euro * 100 + cent
    user = check_register(i)
    to_user = check_register_from_id(who.id)
    if not can_send(user, to_user):
        return await send_success_embed(i, title="Cannot owe this user money",
                                        description="user may have not whitelisted you")
    if not can_send(to_user, user):
        return await send_success_embed(i, title="Cannot owe this user money",
                                        description="you have blocked or not whitelisted this user")
    unique_identifier = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    group = MoneyWriteGroup.create(id=unique_identifier, description=description, created_by=user, type="credit",
                                   picture=attachment.url)
    MoneyWrite.create(group=group, cent_amount=-total_cent, from_user=user, to_user=to_user)
    MoneyWrite.create(group=group, cent_amount=total_cent, from_user=to_user, to_user=user)

    await send_success_embed(i, title=f"Success",
                       description="Successfully recorded {format_euro(total_cent)} debt with <@{to_user.id}>")

# @tree.command(name='give')
# @tree.command(name='accept')
# @tree.command(name='receive')
