from typing import Callable, Awaitable, Any, Iterator, Optional

from discord import ui
import discord
from discord._types import ClientT
from discord.abc import MISSING

from database.database_schema import User


class Select(ui.Select):
    def __init__(self, _callable: Callable[[discord.Interaction, discord.ui.Select], Awaitable[None]],
                 custom_id: str = MISSING,
                 placeholder: str | None = None,
                 min_values: int = 1,
                 max_values: int = 1,
                 options: list[discord.SelectOption] = MISSING,
                 disabled: bool = False,
                 row: int | None = None):
        super().__init__(custom_id=custom_id, placeholder=placeholder, min_values=min_values, max_values=max_values,
                         options=options, disabled=disabled, row=row, )
        self.callable = _callable

    async def callback(self, interaction: discord.Interaction):
        await self.callable(interaction, self)


class Button(ui.Button):
    def __init__(self,
                 _callable: Callable[[discord.Interaction, discord.ui.Button], Awaitable[None]] = None,
                 style: discord.ButtonStyle = discord.ButtonStyle.secondary,
                 label: str | None = None,
                 disabled: bool = False,
                 custom_id: str | None = None,
                 url: str | None = None,
                 emoji: str | discord.Emoji | discord.PartialEmoji | None = None,
                 row: int | None = None):
        super().__init__(style=style, label=label, disabled=disabled, custom_id=custom_id, url=url, emoji=emoji,
                         row=row)
        self.callable = _callable

    async def callback(self, interaction: discord.Interaction):
        if self.callable:
            await self.callable(interaction, self)


class UserSelect(ui.UserSelect):
    def __init__(self, _callable: Callable[[discord.Interaction, discord.ui.UserSelect], Awaitable[None]],
                 custom_id: str = MISSING,
                 placeholder: str | None = None,
                 min_values: int = 1,
                 max_values: int = 1,
                 disabled: bool = False,
                 row: int | None = None):
        super().__init__(custom_id=custom_id, placeholder=placeholder, min_values=min_values, max_values=max_values,
                         disabled=disabled, row=row)
        self.callable = _callable

    async def callback(self, interaction: discord.Interaction[ClientT]) -> Any:
        await self.callable(interaction, self)


class ApplicationView(ui.View):
    last_interaction: discord.Interaction | None
    is_initial = True

    async def set_state(self, interaction: discord.Interaction):
        await self._render(interaction, to_render=self.render())

    def __init__(self, ephemeral: bool = True, timeout: Optional[int] = None):
        super().__init__(timeout=timeout)
        self.ephemeral = ephemeral

    async def _render(self, interaction: discord.Interaction, to_render: Iterator[str | discord.Embed | ui.Item]):
        self.clear_items()
        embed = None
        message_str = None
        for component in to_render:
            if isinstance(component, discord.Embed):
                embed = component
            if isinstance(component, str):
                message_str = component
            if isinstance(component, ui.Item):
                self.add_item(component)

        self.last_interaction = interaction
        if self.is_initial:
            await interaction.response.send_message(embed=embed, view=self, content=message_str,
                                                    ephemeral=self.ephemeral)
            self.is_initial = False
        else:
            await interaction.response.edit_message(embed=embed, view=self, content=message_str)

    def render(self) -> Iterator[str | discord.Embed | ui.Item]:
        ...


class UserApplicationView(ApplicationView):
    def __init__(self, user: User, ephemeral: bool = True, timeout: Optional[int] = None):
        self.user = user
        super().__init__(ephemeral=ephemeral, timeout=timeout)


def render_timeout(self):
    yield discord.Embed(title="Timeout",
                        description="Sorry, this interaction has timeouted, please call this command again",
                        color=0xFF0000)


def on_timeout(self) -> None:
    self.clean_up()
    self._render(self.last_interaction, self.render_timeout())


def stop(self) -> None:
    self.clean_up()
    super().stop()


def clean_up(self):
    ...


async def run_application(interaction: discord.Interaction, application: ApplicationView):
    await application._render(interaction, application.render())
