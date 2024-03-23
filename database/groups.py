import re

from discord import User

from database.database_schema import *

_group_regex = re.compile("[a-z0-9]{5}")
_sub_group_regex = re.compile(r"[a-z0-9]{5}(\([a-z0-9]\)|[a-z0-9])")


def is_group_id(uid: str):
    return bool(_group_regex.fullmatch(uid.lower()))


def is_sub_group_id(uid: str):
    return bool(_sub_group_regex.fullmatch(uid.lower()))


def is_valid_id(uid: str):
    return is_group_id(uid) or is_sub_group_id(uid)


def get_participant(uid: str, user: User):
    uid = uid.upper()
    # TODO: only if uid is group not subgroup
    try:
        if is_group_id(uid):
            return MoneyWriteGroupParticipant.select().join(MoneyWriteGroup).where(
                MoneyWriteGroupParticipant.participant == user.id, MoneyWriteGroupParticipant.group == uid,
                MoneyWriteGroupParticipant.sub_group.is_null()).get()
    except:
        return None


def get_group(uid: str, user: User):
    if not is_group_id(uid):
        return
    uid = uid.upper()
    try:
        return MoneyWriteGroup.select().where(MoneyWriteGroup.id == uid).join(MoneyWriteGroupParticipant).where(
            MoneyWriteGroupParticipant.sub_group.is_null(), MoneyWriteGroupParticipant.participant == user.id)[0]
    except:
        return None


def get_sub_group(uid: str, user: User):
    if not is_sub_group_id(uid):
        return
    uid = uid.upper()
    if len(uid) == 6:
        group_uid = uid[0:5]
        sub_group_uid = uid[5]
    else:
        group_uid = uid.split("(")[0]
        sub_group_uid = uid[6]
    try:
        return MoneyWriteSubGroup.select().where(MoneyWriteSubGroup == sub_group_uid).join(MoneyWriteGroup).join(
            MoneyWriteGroupParticipant,
            on=MoneyWriteGroupParticipant.sub_group == MoneyWriteSubGroup.sub_id &
               MoneyWriteGroupParticipant.group == MoneyWriteGroup.id).where(
            MoneyWriteGroupParticipant.sub_group.is_null(), MoneyWriteGroupParticipant.participant == user.id).where(
            MoneyWriteGroup.id == group_uid).get()
    finally:
        return None
