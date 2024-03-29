from typing import Tuple, Optional, Union, Any, Iterable
import re

import discord
from discord import Emoji, PartialEmoji, Interaction, TextChannel, Message
from discord._types import ClientT
from discord.ui.dynamic import DynamicItem


# only ints and strings allowed
def encode_value(value: int | str | bool) -> str:
    if type(value) == bool:
        return "t" if value else "f"
    return str(value)


def encode_tuple(t: Tuple[int | str, ...]) -> str:
    return ":".join(map(encode_value, t))


def decode_into_tuple(s: str) -> Tuple[int | str, ...]:
    return tuple(map(decode_single_value, s.split(":")))


def decode_single_value(val: str) -> int | str:
    if val == "t":
        return True
    if val == "f":
        return False
    try:
        return int(val)
    except ValueError:
        return val


class Button:
    def __init__(self, button_name: str, disabled: bool = False,
                 style: discord.ButtonStyle = discord.ButtonStyle.blurple,
                 label: str = None,
                 url: Optional[str] = None,
                 emoji: Optional[Union[str, Emoji, PartialEmoji]] = None,
                 row: Optional[int] = None):
        self.button_name = button_name
        self.disabled = disabled
        self.style = style
        self.label = label
        self.url = url
        self.emoji = emoji
        self.row = row


# idee nur ein button wird registriert
# der button kann dann anhand der "payload" entscheiden was zu tun ist
# template=r"nameofcommand:(?P<>data.*)"
# in interaction method check data to know which button was pressed

# in interaction:
# can call "stop" (can be replaced by just rendering without buttons 🤯
# can call "delete"
# can call "setstate" (gives new data + rerenders
class ButtonSystem(DynamicItem[discord.ui.Button], template=""):

    def __init_subclass__(cls, name):
        cls.name = name
        super().__init_subclass__(template=f"{name}:(?P<ephemeral>.):(?P<button_name>\\w+):(?P<data>.*)")

    def __init__(self, data: Tuple[int | str, ...], *, ephemeral: bool, button_name: str = None,
                 button: discord.ui.Button = None, ac_interaction: discord.Interaction = None) -> None:
        self._button_name = button_name
        self._data = data
        self._last_interaction = None
        self._ephemeral = ephemeral
        self._ac_interaction = ac_interaction
        super().__init__(button or discord.ui.Button())

    @property
    def data(self) -> Tuple[int | str, ...]:
        return self._data

    @property
    def button_name(self) -> str:
        return self._button_name

    @property
    def current_interaction(self) -> discord.Interaction:
        return self._last_interaction

    @property
    def ac_interaction(self) -> discord.Interaction:
        return self._ac_interaction

    @property
    def ephemeral(self) -> bool:
        return self._ephemeral

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str], /):
        return cls(decode_into_tuple(match.group("data")), button_name=match.group("button_name"), button=item,
                   ephemeral=match.group("ephemeral") == "e")  # ac_interaction=interaction

    @classmethod
    async def run_system_on_interaction(cls, interaction: Interaction, data: Tuple[str | int, ...], *,
                                        ephemeral: bool = True, is_initial: bool = True):
        button = cls(data=data, ephemeral=ephemeral, button=discord.ui.Button(custom_id=f"{cls.name}:n:a:"),
                     button_name=f"")
        s, embed, view = button.eval_discord_render(interaction)
        if is_initial:
            await interaction.response.send_message(embed=embed, view=view, content=s, ephemeral=ephemeral)
        else:
            await interaction.response.edit_message(embed=embed, view=view, content=s)

    @classmethod
    async def run_system_on_interaction_edit(cls, interaction: Interaction, data: Tuple[str | int, ...], *,
                                             ephemeral: bool = True):
        button = cls(data=data, ephemeral=ephemeral, button=discord.ui.Button(custom_id=f"{cls.name}:n:a:"),
                     button_name=f"")
        s, embed, view = button.eval_discord_render(interaction)
        await interaction.edit_original_response(embed=embed, view=view, content=s)

    @classmethod
    async def run_system_on_channel(cls, channel: TextChannel, data: Tuple[str | int, ...]) -> Message:
        button = cls(data=data, ephemeral=False, button=discord.ui.Button(custom_id=f"{cls.name}:n:a:"), button_name="")
        s, embed, view = button.eval_discord_render()
        return await channel.send(embed=embed, view=view, content=s)

    @classmethod
    async def run_system_on_message(cls, message: Message, data: Tuple[str | int, ...]):
        button = cls(data=data, ephemeral=False, button=discord.ui.Button(custom_id=f"{cls.name}:n:a:"), button_name="")
        s, embed, view = button.eval_discord_render()
        await message.edit(embed=embed, view=view, content=s)

    async def set_state(self, data: Tuple[int | str]):
        self._data = data
        message_str, embed, view = self.eval_discord_render()
        await self._last_interaction.response.edit_message(embed=embed, view=view, content=message_str)

    def eval_discord_render(self, ac_interaction=None) -> (str | None, discord.Embed | None, discord.ui.View | None):
        message_str = ""
        embed = None
        view = discord.ui.View(timeout=None)
        for component in self.render():
            if isinstance(component, discord.Embed):
                embed = component
            if isinstance(component, str):
                message_str += component
            if isinstance(component, Button):
                custom_id = f"{type(self).name}:{"e" if self.ephemeral else "n"}:{component.button_name}:{encode_tuple(self._data)}"
                button = discord.ui.Button(custom_id=custom_id, label=component.label, style=component.style,
                                           disabled=component.disabled,
                                           emoji=component.emoji, url=component.url, row=component.row)

                dynamic_button = type(self)(self._data, button_name=component.button_name, button=button,
                                            ephemeral=self.ephemeral, ac_interaction=ac_interaction)
                view.add_item(dynamic_button)
        return message_str, embed, view

    def render(self) -> Iterable[Button | discord.Embed | str]:
        ...

    async def general_interaction_check(self):
        return True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not await self.general_interaction_check():
            return False
        self._last_interaction = interaction
        check_method_name = "check_" + self.button_name
        check_method = getattr(self, check_method_name, None)
        if check_method:
            return await check_method()
        return True

    async def callback(self, interaction: Interaction[ClientT]) -> Any:
        specific_callback = getattr(self, self._button_name)
        await specific_callback()
