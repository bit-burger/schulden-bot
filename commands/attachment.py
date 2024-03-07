import discord
from discord import app_commands

from .utils import *
from config import tree

image_listener = UserListener()


@tree.command(name='add_image', description="add image or pdf to last supporting command you have been using",
              guild=discord.Object(id=1201588191094906890))
@app_commands.describe(
    image="the image to add"
)
async def add_image(i: discord.Interaction, image: discord.Attachment):
    if not image_listener.exists_listener_for_user(i.user.id):
        return await send_error_embed(i, title="No command you are using can accept an image right now")
    if not attachment_is_image(image):
        return await send_error_embed(i, title="Not an image/pdf",
                                      description="the attachment needs to be an image (png, jpg, etc...) or pdf")
    image_listener.add_event(i.user.id, image.url)
    await send_success_embed(i, title="Successfully added image")


@tree.command(name='edit_image', description="edit image or pdf of last supporting command you have been using",
              guild=discord.Object(id=1201588191094906890))
@app_commands.describe(
    image="the new image/pdf"
)
async def edit_image(i, image: discord.Attachment):
    await add_image(i, image)
