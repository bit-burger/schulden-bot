from enum import Enum
from typing import Any

from database.database_schema import User, UserSettings


class Setting(Enum):
    whitelisting_on = 0
    # whitelist_dm_requests = 1
    max_amount = 2
    send_deletion_requests_per_dm = 3
    send_debts_per_dm = 4
    send_own_debts_per_dm = 5
    debt_interactions_public = 6
    group_debt_interactions_public = 7


_setting_defaults = {
    Setting.whitelisting_on: False,
    Setting.max_amount: 5000,
    Setting.send_deletion_requests_per_dm: True,
    Setting.send_debts_per_dm: True,
    Setting.send_own_debts_per_dm: False,
    Setting.debt_interactions_public: False,
    Setting.group_debt_interactions_public: True,
}


def get_setting(user: User, setting: Setting):
    setting_db_object = UserSettings.get_or_none(user=user, setting=setting.value)
    if setting_db_object:
        return setting_db_object.value
    return _setting_defaults[setting]


def set_setting(user: User, setting: Setting, value: Any):
    UserSettings.insert(user=user, setting=setting.value, value=value).on_conflict_replace().execute()
