from peewee import *
import datetime

db = SqliteDatabase("test.db", pragmas={'foreign_keys': 1})


class BaseModel(Model):
    created_at = DateTimeField(default=datetime.datetime.now)

    class Meta:
        database = db


class RegisteredUser(BaseModel):
    id = IntegerField(primary_key=True)
    deleted_at = DateTimeField(null=True)
    # (whitelisting jeder whitelisted wen anders) send_friend_invites_per_dm = BooleanField(default=False)
    everyone_allowed_per_default = BooleanField(default=True)
    # dm notifications new debt
    # dm notifications new debt übertragung


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


class Debt(BaseModel):
    id: TextField(primary_key=True)
    name: TextField(null=True) # not loaded??????
    description = TextField(null=True)
    guild_channel = ForeignKeyField(GuildChannel, null=True)
    message_id = IntegerField(null=True)
    deleted_at = DateTimeField(null=True)
    creditor = ForeignKeyField(RegisteredUser, null=False, backref="debts_given")


class DebtProof(BaseModel):
    # peewee automatically adds auto increment id field
    debt = ForeignKeyField(Debt, null=False)
    url = TextField(null=False)

class DebtRoleTarget(BaseModel):
    debt = ForeignKeyField(Debt, null=False)
    role_id = IntegerField(null=False)
    role_name = TextField(null=False)

    class Meta:
        primary_key = CompositeKey('debt', 'role_id')


class DebtUserTarget(BaseModel):
    debt = ForeignKeyField(Debt, null=False)
    debtor = ForeignKeyField(RegisteredUser, null=False)
    specific_description = TextField(null=True)
    # if cent_amount is positive this is money that the debtor owes [the creditor]
    # if cent_amount is negative this is money that the debtor has paid [the creditor]
    cent_amount = IntegerField(null=False) # constraints=["cent_amount <> 0"]

    class Meta:
        primary_key = CompositeKey('debt', 'debtor')


def init():
    db.connect()
    db.create_tables([RegisteredUser, GuildChannel, Debt, DebtRoleTarget, DebtUserTarget, IgnoreUsers, WhitelistUser])
