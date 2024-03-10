import discord


async def send_error_embed(interaction: discord.Interaction, title: str = None, description: str = None):
    await interaction.response.send_message(embed=discord.Embed(title=title, description=description, color=0xFF0000))


async def send_success_embed(interaction: discord.Interaction, title: str = None, description: str = None):
    await interaction.response.send_message(embed=discord.Embed(title=title, description=description, color=0x00FF00))


def attachment_is_image(attachment: discord.Attachment):
    return attachment.content_type.startswith("image/") or attachment.content_type == "application/pdf"
