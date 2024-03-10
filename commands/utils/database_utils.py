import discord

from database.database_schema import RegisteredUser


def check_register(interaction: discord.Interaction) -> RegisteredUser:
    return check_register_from_id(interaction.user.id)


def check_register_from_id(id_: int) -> RegisteredUser:
    user, created = RegisteredUser.get_or_create(id=id_)
    return user
