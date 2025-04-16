import uuid
from tortoise import fields
from tortoise.models import Model
import enum


class OperationType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"


class BalanceHistory(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    user = fields.ForeignKeyField("models.User", related_name="balance_history")
    instrument = fields.ForeignKeyField("models.Instrument", related_name="balance_history")
    amount = fields.IntField()
    operation_type = fields.CharEnumField(OperationType)
    executed_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "balance_history"