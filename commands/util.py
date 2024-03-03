import discord
from discord import ui, SelectOption, ButtonStyle, Emoji, PartialEmoji, Interaction
from discord._types import ClientT
from discord.abc import MISSING
from typing import Callable, Optional, Iterator, Any, Awaitable

from database import RegisteredUser


def check_register(interaction: discord.Interaction) -> RegisteredUser:
    user, created = RegisteredUser.get_or_create(id=interaction.user.id)
    return user


def check_register_from_id(id: int) -> RegisteredUser:
    user, created = RegisteredUser.get_or_create(id=id)
    return user


class ApplicationState:
    item_list: [ui.Item]
    embed: discord.Embed
    message_string: str

    def __init__(self, item_list: [ui.Item], embed: discord.Embed, message_string: str):
        self.item_list = item_list
        self.embed = embed
        self.message_string = message_string


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


class Application(ui.View):
    def __init__(self, state: any):
        super().__init__()
        self.state = state

    # def renderTimeout(self) -> ApplicationState:
    #     ...


class ApplicationView(ui.View):
    _state: any
    user: RegisteredUser
    _interaction: discord.Interaction | None

    @property
    def state(self):
        return self._state

    async def set_state(self, state: any, interaction: discord.Interaction):
        self._state = state
        await self._render(interaction, is_initial=False)

    def __init__(self, state: any, user: RegisteredUser, ephemeral: bool = True):
        super().__init__()
        self.ephemeral = ephemeral
        self._state = state
        self.user = user

    async def _render(self, interaction: discord.Interaction, is_initial: bool):
        self.clear_items()
        embed = None
        message_str = None
        for component in self.render():
            if isinstance(component, discord.Embed):
                embed = component
            if isinstance(component, str):
                message_str = str
            if isinstance(component, ui.Item):
                self.add_item(component)

        if is_initial:
            await interaction.response.send_message(embed=embed, view=self, content=message_str,
                                                    ephemeral=self.ephemeral)
            self._interaction = interaction
        else:
            await interaction.response.edit_message(embed=embed, view=self, content=message_str)

    def render(self) -> Iterator[str | discord.Embed | ui.Item]:
        ...


async def run_application(interaction: discord.Interaction, application: ApplicationView):
    await application._render(interaction, is_initial=True)

    # def on_timeout(self) -> None:


def to_id_set(users: [discord.User | discord.Member]) -> {int}:
    return set(map(lambda user: user.id, users))


def id_iter_to_text(ids: {int}) -> str:
    return ",".join(map(lambda id: "<@" + str(id) + ">", ids))
