from database.database_schema import *
from peewee import *


def exe(sql: str, params: [any]):
    return RawQuery(sql, params).execute(db)


# balance of the user with each other user (but without ignored and with whitelist)
def user_balance_cte(user: RegisteredUser):
    to_user_alias = RegisteredUser.alias("to_user")
    from_user_alias = RegisteredUser.alias("from_user")

    user_id_column = to_user_alias.id.alias("user_id")
    cent_amount_column = fn.sum(MoneyWrite.cent_amount).alias("total_cent_amount")

    whitelist_query = user.whitelisted.select(WhitelistUser.whitelisted)

    return (user.money_writes
            .select(user_id_column, cent_amount_column)
            .join(to_user_alias, on=MoneyWrite.to_user == to_user_alias.id)
            .switch(MoneyWrite)
            .join(MoneyWriteGroup)
            .where(MoneyWriteGroup.deleted_at.is_null() & (user.everyone_allowed_per_default | user_id_column.in_(whitelist_query)))
            .group_by(user_id_column)).cte('money_write_nets', columns=('user_id', 'cent_amount'))


# credit_first: (should be ordered by the highest credit)
# page_size: how big the list should be
# page: starts by 0
def user_balance(user: RegisteredUser, credit_first: bool, page_size: int, page: int):
    cte = user_balance_cte(user)
    order_column = cte.c.cent_amount
    if not credit_first:
        order_column = order_column
    return (cte
            .select_from(cte.c.user_id, cte.c.cent_amount)
            .order_by(order_column)
            .paginate(page + 1, page_size).dicts())


# gives back (credit, database)
def user_credit_and_debt(user: RegisteredUser) -> (int, int):
    cte = user_balance_cte(user)
    # select on cte instead of with_cte ?
    credit = cte.select_from(fn.sum(cte.c.cent_amount)).where(cte.c.cent_amount > 0)
    debt = cte.select_from(fn.sum(0 - cte.c.cent_amount)).where(cte.c.cent_amount < 0)

    return credit[0].cent_amount or 0, debt[0].cent_amount or 0  # use .tuples() ?
