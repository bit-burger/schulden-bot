from typing import Literal, Optional, Iterable

import discord

from commands.utils.persistent_view import ButtonSystem, Button
from config import tree


class ExamplePersistent(ButtonSystem, name="ep"):
    async def increment(self):
        await self.set_state((self.data[0] + 1,))

    def render(self) -> Iterable[Button | discord.Embed | str]:
        yield Button(button_name="increment", label=str(self.data[0]))


@tree.command(name='example', description="history of debt with single person",
              guild=discord.Object(id=1201588191094906890))
async def view(interaction: discord.Interaction, ok: int):
    await ExamplePersistent.run_system(interaction, (ok,))
