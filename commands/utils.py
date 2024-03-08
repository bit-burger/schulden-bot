import re

import discord
from discord import ui, SelectOption, ButtonStyle, Emoji, PartialEmoji, Interaction
from discord._types import ClientT
from discord.abc import MISSING
from typing import Callable, Iterator, Any, Awaitable, Optional

import config
from config import client
from database.database_schema import RegisteredUser


def check_register(interaction: discord.Interaction) -> RegisteredUser:
    return check_register_from_id(interaction.user.id)


def check_register_from_id(id_: int) -> RegisteredUser:
    user, created = RegisteredUser.get_or_create(id=id_)
    return user


async def send_error_embed(interaction: Interaction, title: str = None, description: str = None):
    await interaction.response.send_message(embed=discord.Embed(title=title, description=description, color=0xFF0000))


async def send_success_embed(interaction: Interaction, title: str = None, description: str = None):
    await interaction.response.send_message(embed=discord.Embed(title=title, description=description, color=0x00FF00))


def format_euro(cent: int) -> str:
    after_point = str(cent % 100)
    if len(after_point) == 1:
        after_point = "0" + after_point
    return f"{cent // 100}.{after_point}€"


euro_regex = re.compile(r"(?=.?\d)\d*[.,]?\d{0,2}")
euro_split_regex = re.compile("[,.]")


def str_to_euro_cent(s: str) -> Optional[int]:
    s = s.replace(" ", "").replace("\t", "").replace("\n", "").replace("€", "")
    if not euro_regex.fullmatch(s):
        return None
    split = euro_split_regex.split(s)
    val = 0
    if split[0] != "":
        val = int(split[0]) * 100
    if len(split) > 1 and split[1] != "":
        if len(split[1]) == 1:
            val += int(split[1]) * 10
        else:
            val += int(split[1])
    return val


def get_id_of_slash_command(name: str):
    return next(c for c in config.commands if c.name == name).id


def mention_slash_command(name: str):
    return f"</{name}:{get_id_of_slash_command(name)}>"

def mention_timestamp(timestamp, type):
    return f"<t:{timestamp}:R>"

def mention_relative_timestamp(timestamp):
    return mention_timestamp(timestamp, "R")


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
    last_interaction: discord.Interaction | None
    is_initial = True

    @property
    def state(self):
        return self._state

    async def set_state(self, state: any, interaction: discord.Interaction, follow_up=False):
        self._state = state
        await self._render(interaction, to_render=self.render(), follow_up=follow_up)

    def __init__(self, state: any, user: RegisteredUser, ephemeral: bool = True, timeout: Optional[int] = None):
        super().__init__(timeout=timeout)
        self.ephemeral = ephemeral
        self._state = state
        self.user = user

    async def _render(self, interaction: discord.Interaction, to_render: Iterator[str | discord.Embed | ui.Item],
                      follow_up=False):
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
        if follow_up:
            response = await interaction.original_response()
            await interaction.followup.send(embed=embed, view=self, content=message_str)
        elif self.is_initial:
            await interaction.response.send_message(embed=embed, view=self, content=message_str,
                                                    ephemeral=self.ephemeral)
            self.is_initial = False
        else:
            await interaction.response.edit_message(embed=embed, view=self, content=message_str)

    def render(self) -> Iterator[str | discord.Embed | ui.Item]:
        ...


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

    # def on_timeout(self) -> None:


def to_id_set(users: [discord.User | discord.Member]) -> {int}:
    return set(map(lambda user: user.id, users))


def id_iter_to_text(ids: {int}) -> str:
    return ",".join(map(lambda id: "<@" + str(id) + ">", ids))


def attachment_is_image(attachment: discord.Attachment):
    return attachment.content_type.startswith("image/") or attachment.content_type == "application/pdf"


class UserListener:
    listeners = {}

    def add_listener(self, user_id, listener):
        self.listeners[user_id] = listener

    def remove_listener(self, user_id):
        if user_id in self.listeners:
            self.listeners.pop(user_id)

    def exists_listener_for_user(self, user_id):
        return user_id in self.listeners

    def add_event(self, user_id, event):
        self.listeners[user_id].event(event)

    async def async_add_event(self, user_id, event):
        await self.listeners[user_id].event(event)
