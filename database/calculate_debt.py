import math

from database.database_schema import *
from peewee import *


def exe(sql: str, params: [any]):
    return RawQuery(sql, params).execute(db)


# balance of the user with each other user (but without ignored and with whitelist)
def _user_balance_cte(user: User):
    to_user_alias = User.alias("to_user")
    from_user_alias = User.alias("from_user")

    user_id_column = to_user_alias.id.alias("user_id")
    cent_amount_column = fn.sum(MoneyWrite.cent_amount).alias("total_cent_amount")

    whitelist_query = user.whitelisted.select(WhitelistUser.whitelisted)

    return (user.money_writes
            .select(user_id_column, cent_amount_column)
            .join(to_user_alias, on=MoneyWrite.to_user == to_user_alias.id)
            .switch(MoneyWrite)
            .join(MoneyWriteSubGroup)
            .where(MoneyWriteSubGroup.deleted_at.is_null() & (
            user.everyone_allowed_per_default | user_id_column.in_(whitelist_query)))
            .group_by(user_id_column)).cte('money_write_nets', columns=('user_id', 'cent_amount'))


# credit_first: (should be ordered by the highest credit)
# page_size: how big the list should be
# page: starts by 0
def user_balance(user: User, credit_first: bool, page_size: int, page: int):
    cte = _user_balance_cte(user)
    order_column = cte.c.cent_amount
    if not credit_first:
        order_column = order_column.desc()
    return (cte
            .select_from(cte.c.user_id, cte.c.cent_amount)
            .order_by(order_column)
            .paginate(page + 1, page_size).dicts())


def user_balance_page_count(user: User, page_size: int) -> int:
    cte = _user_balance_cte(user)
    count = cte.select_from(fn.count(cte.c.user_id)).tuples()[0][0]
    return math.ceil(count / page_size)


# gives back (credit, database)
def user_credit_and_debt(user: User) -> (int, int):
    cte = _user_balance_cte(user)
    # select on cte instead of with_cte ?
    credit = cte.select_from(fn.sum(0 - cte.c.cent_amount)).where(cte.c.cent_amount < 0)
    debt = cte.select_from(fn.sum(cte.c.cent_amount)).where(cte.c.cent_amount > 0)

    return credit[0].cent_amount or 0, debt[0].cent_amount or 0  # use .tuples() ?


def _concat_columns(ls):
    res = ls[0]
    for s in ls[1:]:
        res = res.concat(s)
    return res


def _user_history_base(user: User, with_other: User, desc_max_length):
    too_long_cond = fn.LENGTH(MoneyWriteGroup.description) > desc_max_length
    desc_is_null = MoneyWriteGroup.description.is_null()
    desc_in_case_too_long = _concat_columns((fn.substr(MoneyWriteGroup.description, 0, desc_max_length - 3), ".."))

    desc = Case(None, ((desc_is_null, None), (too_long_cond, desc_in_case_too_long)),
                MoneyWriteGroup.description).alias("description")

    # has_sub_id = MoneyWriteSubGroup.unique_sub_identifier.is_null(False)
    # full_id = _concat_columns((MoneyWriteGroup.id, "(", MoneyWriteSubGroup.unique_sub_identifier, ")"))
    # unique_id = Case(None, ((has_sub_id, full_id),), MoneyWriteGroup.id).alias("id")

    return MoneyWrite.select(
        MoneyWriteGroup.id,
        MoneyWriteSubGroup.deleted_at.is_null(False).alias("is_deleted"),
        MoneyWriteSubGroup.sub_id,
        MoneyWrite.cent_amount,
        MoneyWriteGroup.created_by,
        MoneyWriteGroup.created_at,
        desc,
        MoneyWriteGroup.type,
    ).switch(MoneyWrite).join(MoneyWriteSubGroup).switch(MoneyWriteSubGroup).join(MoneyWriteGroup).where(
        MoneyWrite.from_user == user.id, MoneyWrite.to_user == with_other.id)


def user_history(user: User, with_other: User, desc_max_length, page_size, page,
                 newest_first):
    base = _user_history_base(user, with_other, desc_max_length)
    order_column = MoneyWriteGroup.created_at
    if newest_first:
        order_column = order_column.desc()
    return (base
            .order_by(order_column)
            .paginate(page + 1, page_size).dicts())


def user_history_page_count(user: User, with_other: User, page_size):
    count = \
        user.money_writes.select(fn.count(MoneyWrite.from_user)).where(MoneyWrite.to_user == with_other.id).tuples()[0][
            0]
    return math.ceil(count / page_size)


def total_balance_with_user(user: User, with_other: User):
    return \
        user.money_writes.select(fn.sum(MoneyWrite.cent_amount)).switch(MoneyWrite).join(MoneyWriteSubGroup).where(
            MoneyWrite.to_user == with_other.id,  MoneyWriteSubGroup.deleted_at.is_null()).tuples()[0][
            0] or 0
