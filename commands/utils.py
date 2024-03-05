import discord
from discord import ui, SelectOption, ButtonStyle, Emoji, PartialEmoji, Interaction
from discord._types import ClientT
from discord.abc import MISSING
from typing import Callable, Iterator, Any, Awaitable

from database.database_schema import RegisteredUser


def check_register(interaction: discord.Interaction) -> RegisteredUser:
    return check_register_from_id(interaction.user.id)


def check_register_from_id(id_: int) -> RegisteredUser:
    user, created = RegisteredUser.get_or_create(id=id_)
    return user


class Select(ui.Select):
    def __init__(self, _callable: Callable[[discord.Interaction, discord.ui.Select], Awaitable[None]],
                 custom_id: str = MISSING,
                 placeholder: str | None = None,
                 min_values: int = 1,
                 max_values: int = 1,
                 options: list[SelectOption] = MISSING,
                 disabled: bool = False,
                 row: int | None = None):
        super().__init__(custom_id=custom_id, placeholder=placeholder, min_values=min_values, max_values=max_values,
                         options=options, disabled=disabled, row=row, )
        self.callable = _callable

    async def callback(self, interaction: discord.Interaction):
        await self.callable(interaction, self)


class Button(ui.Button):
    def __init__(self,
                 _callable: Callable[[discord.Interaction, discord.ui.Button], Awaitable[None]],
                 style: ButtonStyle = ButtonStyle.secondary,
                 label: str | None = None,
                 disabled: bool = False,
                 custom_id: str | None = None,
                 url: str | None = None,
                 emoji: str | Emoji | PartialEmoji | None = None,
                 row: int | None = None):
        super().__init__(style=style, label=label, disabled=disabled, custom_id=custom_id, url=url, emoji=emoji,
                         row=row)
        self.callable = _callable

    async def callback(self, interaction: discord.Interaction):
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

    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        await self.callable(interaction, self)


class ApplicationView(ui.View):
    _state: any
    user: RegisteredUser
    _interaction: discord.Interaction | None
    is_initial = True

    @property
    def state(self):
        return self._state

    async def set_state(self, state: any, interaction: discord.Interaction):
        self._state = state
        await self._render(interaction, to_render=self.render())

    def __init__(self, state: any, user: RegisteredUser, ephemeral: bool = True):
        super().__init__()
        self.ephemeral = ephemeral
        self._state = state
        self.user = user

    async def _render(self, interaction: discord.Interaction, to_render: Iterator[str | discord.Embed | ui.Item]):
        self.clear_items()
        embed = None
        message_str = None
        for component in to_render:
            if isinstance(component, discord.Embed):
                embed = component
            if isinstance(component, str):
                message_str = str
            if isinstance(component, ui.Item):
                self.add_item(component)

        self._interaction = interaction
        if self.is_initial:
            await interaction.response.send_message(embed=embed, view=self, content=message_str,
                                                    ephemeral=self.ephemeral)
            self.is_initial = False
        else:
            await interaction.response.edit_message(embed=embed, view=self, content=message_str)

    def render(self) -> Iterator[str | discord.Embed | ui.Item]:
        ...

    def timeout_render(self):
        yield discord.Embed(title="Timeout",
                            description="Sorry, this interaction has timeouted, please call this command again",
                            color=0xFF0000)

    def on_timeout(self) -> None:
        self._render(self._interaction, self.timeout_render())


async def run_application(interaction: discord.Interaction, application: ApplicationView):
    await application._render(interaction, is_initial=True)

    # def on_timeout(self) -> None:


def to_id_set(users: [discord.User | discord.Member]) -> {int}:
    return set(map(lambda user: user.id, users))


def id_iter_to_text(ids: {int}) -> str:
    return ",".join(map(lambda id: "<@" + str(id) + ">", ids))
