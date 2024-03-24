from typing import Literal

import discord

from commands.utils.formatting import mention_slash_command, format_euro
from database.settings import *


def ephemeral_from_arg(user: User, show_arg: str | None):
    if not show_arg:
        return bool(get_setting(user, Setting.debt_interactions_public))
    return show_arg != "yes"


def ephemeral_group_from_arg(user: User, show_arg: Literal["yes", "no"] | None):
    if not show_arg:
        return bool(get_setting(user, Setting.group_debt_interactions_public))
    return show_arg != "yes"


def check_register(interaction: discord.Interaction) -> User:
    return check_register_from_id(interaction.user.id)


def check_register_from_id(id_: int) -> User:
    user, created = User.get_or_create(id=id_)
    return user


def max_interaction_amount(*users: User) -> int:
    max_amount = 0
    for user in users:
        max_amount = max(max_amount, get_setting(user, Setting.max_amount))
    return max_amount


def max_interaction_error(you: User, other: User, amount: int, human_readable_format: bool = False) -> str | None:
    max_amount_you = max_interaction_amount(you)
    if max_amount_you < amount:
        return (f"Your {setting_names[Setting.max_amount]} is at `{format_euro(max_amount_you)}`, "
                f"but the amount is `{format_euro(amount)}`."
                f"Please change it in {"/settings" if human_readable_format else mention_slash_command("settings")}"
                f"if you want to allow a higher amount of money"
                )
    max_amount_other = max_interaction_amount(other)
    if max_amount_other < amount:
        return (f"The {setting_names[Setting.max_amount]} of <@{other.id}> is at `{format_euro(max_amount_you)}`, "
                f"but the amount is `{format_euro(amount)}`."
                )
