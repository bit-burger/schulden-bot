from database.database_schema import *


# if b has allowed a by allowing all (and not ignoring), or by whitelisting
def can_send(a: RegisteredUser, b: RegisteredUser) -> bool:
    if b.everyone_allowed_per_default:
        return True
    whitelist = WhitelistUser.get_or_none(WhitelistUser.by == b.id, WhitelistUser.whitelisted == a)
    if whitelist:
        return True
    return False
