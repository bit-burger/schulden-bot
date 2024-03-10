import re

import discord
from typing import Optional

import config


def format_euro(cent: int) -> str:
    after_point = str(cent % 100)
    if len(after_point) == 1:
        after_point = "0" + after_point
    return f"{cent // 100}.{after_point}€"


def format_euro_sign(cent: int, deleted=False) -> str:
    emoji = sign_emoji(cent, deleted=deleted)
    cent = abs(cent)
    return f"{emoji}`{format_euro(cent)}`"


_euro_regex = re.compile(r"(?=.?\d)\d*[.,]?\d{0,2}")
_euro_split_regex = re.compile("[,.]")


def str_to_euro_cent(s: str) -> Optional[int]:
    s = s.replace(" ", "").replace("\t", "").replace("\n", "").replace("€", "")
    if not _euro_regex.fullmatch(s):
        return None
    split = _euro_split_regex.split(s)
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


# t	  16:20	                        Short Time
# T	  16:20:30	                    Long Time
# d	  20/04/2021	                Short Date
# D	  20 April 2021	                Long Date
# f   April 2021 16:20	            Short Date/Time
# F	  Tuesday, 20 April 2021 16:20	Long Date/Time
# R	  2 months ago	                Relative Time
def mention_timestamp(timestamp, type):
    return f"<t:{timestamp}:{type}>"


def mention_relative_timestamp(timestamp):
    return mention_timestamp(int(timestamp), "R")


def pad_to_len(s, length):
    if len(s) <= length:
        return s + " " * (length - len(s))


def sign_emoji(a, deleted=False):
    if a < 0:
        if deleted:
            return config.minus_grey_emoji
        return config.minus_emoji
    elif deleted:
        return config.plus_grey_emoji
    return config.plus_emoji


def to_id_set(users: [discord.User | discord.Member]) -> {int}:
    return set(map(lambda user: user.id, users))


def id_iter_to_text(ids: {int}) -> str:
    return ",".join(map(lambda id: "<@" + str(id) + ">", ids))
