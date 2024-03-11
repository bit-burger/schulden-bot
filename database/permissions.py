from database.database_schema import *
from .settings import *


# if b has allowed a by allowing all (and not ignoring), or by whitelisting
def can_send(a: User, b: User) -> bool:
    b_whitelisting_on = get_setting(b, Setting.whitelisting_on)
    if not b_whitelisting_on:
        return True
    whitelist = WhitelistUser.get_or_none(WhitelistUser.by == b.id, WhitelistUser.whitelisted == a)
    if whitelist:
        return True
    return False
