from peewee import *
import datetime

from config import db


class BaseModel(Model):
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db
        strict_table = True


class RegisteredUser(BaseModel):
    id = IntegerField(primary_key=True)
    deleted_at = DateTimeField(null=True)
    # (whitelisting jeder whitelisted wen anders) send_friend_invites_per_dm = BooleanField(default=False)
    everyone_allowed_per_default = BooleanField(default=True)
    # dm notifications new database
    # dm notifications new database übertragung


class IgnoreUsers(BaseModel):
    by = ForeignKeyField(RegisteredUser, backref="ignored")
    ignored = ForeignKeyField(RegisteredUser, backref="ignored_by")

    class Meta:
        primary_key = CompositeKey('by', 'ignored')


class WhitelistUser(BaseModel):
    by = ForeignKeyField(RegisteredUser, backref="whitelisted")
    whitelisted = ForeignKeyField(RegisteredUser, backref="whitelisted_by")

    class Meta:
        primary_key = CompositeKey('by', 'whitelisted')


# class Repayment(BaseModel):
#     canceled = ForeignKeyField(RegisteredUser, null=True)
#     cancelReason = TextField(null=True)
#     cent_amount = IntegerField(null=False)
#     method = TextField(null=True)
#     description = TextField()


class GuildChannel(BaseModel):
    id = IntegerField(primary_key=True)
    guild = IntegerField(null=True)


# class DebtRoleTarget(BaseModel):
#     database = ForeignKeyField(Debt, null=False)
#     role_id = IntegerField(null=False)
#     role_name = TextField(null=False)
#
#     class Meta:
#         primary_key = CompositeKey('database', 'role_id')


class MoneyWriteGroup(BaseModel):
    id = TextField(primary_key=True)
    description = TextField(null=True)
    picture = TextField(null=True)
    deleted_at = DateTimeField(null=True)
    guild_channel = ForeignKeyField(GuildChannel, null=True)
    type = TextField()  # money_give, credit, group_credit (maybe schuldenaustausch: switch von schulden von min. 3 person)
    created_by = ForeignKeyField(RegisteredUser)


# EXAMPLE:
# from_user: 1, to_user: 2, cent_amount: -1000
# means:
# - 1 gives 2 10$
# - 1 gives 2 10$ in credit
# - 2 owes 1 10$
# => from user is 10$ in minus, needs 10$

# from_user: 1, to_user: 2, cent_amount: 1000
# means:
# - 2 gives 1 10$
# - 2 gives 1 10$ in credit
# - 1 owes 2 10$
# => from_user is 10$ in plus, got 10$ too much
class MoneyWrite(BaseModel):
    group = ForeignKeyField(MoneyWriteGroup)
    from_user = ForeignKeyField(RegisteredUser, backref="money_writes")
    to_user = ForeignKeyField(RegisteredUser)
    cent_amount = IntegerField()
    specific_description = TextField(null=True)

    class Meta:
        table_name = "money_write"
        # primary_key = CompositeKey('group', 'from_user', 'to_user')
        constraints = [
            SQL("UNIQUE (group_id, from_user_id, to_user_id)"),
            SQL("FOREIGN KEY (group_id, from_user_id, to_user_id) " +
                " REFERENCES money_write(group_id, to_user_id, from_user_id)")]


### Table Audit Log
# Records: creation, editing, and deletion of money writes
# including all attributes by editing with json

# editing money amount after 10 minutes requires approval of other person?


def init():
    db.connect()
    db.create_tables([RegisteredUser, GuildChannel, MoneyWriteGroup, MoneyWrite, IgnoreUsers, WhitelistUser])
