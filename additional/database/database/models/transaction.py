import uuid
from tortoise import fields
from tortoise.models import Model
from .instrument import Instrument
from .order import Order


class Transaction(Model):
    id = fields.UUIDField(primary_key=True, default=uuid.uuid4)
    instrument: fields.ForeignKeyRelation["Instrument"] = fields.ForeignKeyField(
        "models.Instrument", related_name="transactions", on_delete=fields.CASCADE
    )
    quantity = fields.IntField()
    price = fields.IntField()
    buyer_order: fields.ForeignKeyRelation["Order"] = fields.ForeignKeyField(
        "models.Order",
        related_name="buy_transactions",
        on_delete=fields.CASCADE,
    )
    seller_order: fields.ForeignKeyRelation["Order"] = fields.ForeignKeyField(
        "models.Order",
        related_name="sell_transactions",
        on_delete=fields.CASCADE,
    )
    executed_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "transactions"
