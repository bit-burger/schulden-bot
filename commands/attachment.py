from discord import app_commands

from .utils.discord_utils import *
from .utils.formatting import *
from .utils.user_listener import UserListener
from config import tree

image_listener = UserListener()


async def change_image(i, image: discord.Attachment):
    if not image_listener.exists_listener_for_user(i.user.id):
        return await send_error_embed(i, title="No command you are using can accept an image right now")
    if not attachment_is_image(image):
        return await send_error_embed(i, title="Not an image/pdf",
                                      description="the attachment needs to be an image (png, jpg, etc...) or pdf")
    await image_listener.async_add_event(i.user.id, (i, image.url))


@tree.command(name='add_image', description="add image or pdf (will be converted to image) to last supporting command "
                                            "you have been using", guild=discord.Object(config.test_guild_id) if config.test_guild_id else None)
@app_commands.describe(
    image="the image to add"
)
async def add_image(i: discord.Interaction, image: discord.Attachment):
    await change_image(i, image)


@tree.command(name='edit_image', description="edit image or pdf of last supporting command you have been using", guild=discord.Object(config.test_guild_id) if config.test_guild_id else None)
@app_commands.describe(
    image="the new image/pdf"
)
async def edit_image(i, image: discord.Attachment):
    await change_image(i, image)
