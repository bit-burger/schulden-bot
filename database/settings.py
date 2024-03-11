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


setting_names = {
    Setting.whitelisting_on: "enable whitelisting",
    Setting.max_amount: "max debt amount",
    Setting.send_debts_per_dm: "send debt",
    Setting.send_own_debts_per_dm: "send own debts",
    Setting.send_deletion_requests_per_dm: "send debt deletion requests",
    Setting.debt_interactions_public: "private debt interactions public",
    Setting.group_debt_interactions_public: "group debt interaction public",
}

setting_short_descriptions = {
    Setting.whitelisting_on: "Should whitelisting be enabled?",
    Setting.max_amount: "Maximum amount of money you allow per interaction",
    Setting.send_debts_per_dm: "Should a dm be sent if someone else registers debt with you?",
    Setting.send_own_debts_per_dm: "Should a dm be sent each time if you register debt?",
    Setting.send_deletion_requests_per_dm: "Maximum amount of money you allow per interaction",
    Setting.debt_interactions_public: "Should the command messages for private debt be public",
    Setting.group_debt_interactions_public: "Should the command messages for group debt be public?",
}

setting_long_descriptions = {
    Setting.whitelisting_on: "If whitelisting is enabled, this means you can only register debt with people "
                             "you have whitelisted "
                             "(and other people can only register debt with you if you have whitelisted them).",
    Setting.max_amount: "For each debt register the maximum amount of money that is allowed ",
    Setting.send_debts_per_dm: "Should a dm be sent if someone else registers debt with you?",
    Setting.send_own_debts_per_dm: "Should a dm be sent each time if you register debt?",
    Setting.send_deletion_requests_per_dm: "Maximum amount of money you allow per interaction",
    Setting.debt_interactions_public: "Should the command messages with the bot be made public in a server, "
                                      "if it is concerning private debts "
                                      "(the debts registered between only you and a single other user)?",
    Setting.group_debt_interactions_public: "Should the command messages with the bot be made public in a server, "
                                            "if it is concerning group debts "
                                            "(the debts registered between you and multiple users)?",
}

setting_order = [Setting.whitelisting_on,
                 Setting.max_amount,
                 Setting.send_debts_per_dm,
                 Setting.send_own_debts_per_dm,
                 Setting.send_deletion_requests_per_dm,
                 Setting.debt_interactions_public,
                 Setting.group_debt_interactions_public,
                 ]


def get_setting(user: User, setting: Setting):
    setting_db_object = UserSettings.get_or_none(user=user, setting=setting.value)
    if setting_db_object:
        return setting_db_object.value
    return _setting_defaults[setting]


def set_setting(user: User, setting: Setting, value: Any):
    UserSettings.insert(user=user, setting=setting.value, value=value).on_conflict_replace().execute()
