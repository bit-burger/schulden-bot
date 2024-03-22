from peewee import *
import datetime

from config import db


class BaseModel(Model):
    class Meta:
        database = db
        strict_table = True


class User(BaseModel):
    id = IntegerField(primary_key=True)
    deleted_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.datetime.now)


class UserSettings(BaseModel):
    user = ForeignKeyField(User)
    setting = IntegerField()
    value = Field(null=True)

    class Meta:
        table_name = "user_settings"
        constraints = [
            SQL("UNIQUE (user_id, setting)")
        ]


class IgnoreUsers(BaseModel):
    by = ForeignKeyField(User, backref="ignored")
    ignored = ForeignKeyField(User, backref="ignored_by")

    class Meta:
        primary_key = CompositeKey('by', 'ignored')


class WhitelistUser(BaseModel):
    by = ForeignKeyField(User, backref="whitelisted")
    whitelisted = ForeignKeyField(User, backref="whitelisted_by")

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
    description_edited = BooleanField(default=False)
    image_url = TextField(null=True)
    image_url_edited = BooleanField(default=False)
    guild_channel = ForeignKeyField(GuildChannel, null=True)
    type = TextField()  # money_give, credit, group_credit (maybe schuldenaustausch: switch von schulden von min. 3 person)
    created_by = ForeignKeyField(User)
    created_at = DateTimeField(default=datetime.datetime.now)


# example: MoneyWriteGroup has identifier A45CH
#          MoneyWriteSubGroup has identifier b
#          => get to MoneySubWriteGroup: A45CH(b)
class MoneyWriteSubGroup(BaseModel):
    sub_id = TextField(null=True)  # should be a single letter or null if there is only one sub group
    group = ForeignKeyField(MoneyWriteGroup, backref="sub_groups")
    specific_description = TextField(null=True)
    deleted_at = DateTimeField(null=True)
    edited = BooleanField(default=False)


# if want to check if someone can delete whole group,
# just look if they are owner and it is type "group_debt"
# all participants can edit description etc

# for group debts, no matter if the user is the group_debtor or not,
# they should always get a participant for the group and for the sub_group
# but the debtor gets for every sub_group

# if only you are participant with no permissions => only view the debt

# but for simple debts, only group is needed, as you cannot view per sub group (no unique identifier for the sub_group)
class MoneyWriteGroupParticipant(BaseModel):
    group = ForeignKeyField(MoneyWriteGroup)
    sub_group = ForeignKeyField(MoneyWriteSubGroup, null=True)
    participant = ForeignKeyField(User)
    can_request_deletion = BooleanField(default=False)
    can_delete = BooleanField(default=False)


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
    sub_group = ForeignKeyField(MoneyWriteSubGroup, backref="money_writes")
    from_user = ForeignKeyField(User, backref="money_writes")
    to_user = ForeignKeyField(User)
    cent_amount = IntegerField()

    class Meta:
        constraints = [
            SQL("UNIQUE (sub_group_id, from_user_id, to_user_id)"),
            SQL("FOREIGN KEY (sub_group_id, from_user_id, to_user_id) " +
                " REFERENCES moneywrite(sub_group_id, to_user_id, from_user_id)")]


### Table Audit Log
# Records: creation, editing, and deletion of money writes
# including all attributes by editing with json

# editing money amount after 10 minutes requires approval of other person?
class AuditLog(BaseModel):
    group = ForeignKeyField(MoneyWriteGroup)
    sub_group = ForeignKeyField(MoneyWriteSubGroup)
    type: TextField()  # create, delete, edit


class ViewDebtEntryMessages(BaseModel):
    debt_entry = TextField()
    user_id = IntegerField()
    channel_id = IntegerField()
    message_id = IntegerField()
    created_at = DateTimeField(default=datetime.datetime.now)


def init():
    db.connect()
    db.create_tables(
        [User, UserSettings, GuildChannel, MoneyWriteGroup, MoneyWriteSubGroup, MoneyWriteGroupParticipant, MoneyWrite,
         IgnoreUsers, WhitelistUser, ViewDebtEntryMessages])
