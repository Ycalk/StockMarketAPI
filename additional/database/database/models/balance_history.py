from tortoise import fields
from tortoise.models import Model
import enum


class OperationType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"


class BalanceHistory(Model):
    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField(
        "models.User", related_name="balance_history", on_delete=fields.CASCADE
    )
    instrument = fields.ForeignKeyField(
        "models.Instrument", related_name="balance_history", on_delete=fields.NO_ACTION
    )
    amount = fields.IntField()
    operation_type = fields.CharEnumField(OperationType)
    executed_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "balance_history"
