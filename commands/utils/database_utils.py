import discord

from database.database_schema import User


def check_register(interaction: discord.Interaction) -> User:
    return check_register_from_id(interaction.user.id)


def check_register_from_id(id_: int) -> User:
    user, created = User.get_or_create(id=id_)
    return user
