import uuid
from tortoise import fields
from tortoise.models import Model


class Transaction(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    instrument = fields.ForeignKeyField(
        "models.Instrument", related_name="transactions", on_delete=fields.NO_ACTION
    )
    quantity = fields.IntField()
    price = fields.IntField()
    buyer_order = fields.ForeignKeyField(
        "models.Order",
        related_name="buy_transactions",
        null=True,
        on_delete=fields.NO_ACTION,
    )
    seller_order = fields.ForeignKeyField(
        "models.Order",
        related_name="sell_transactions",
        null=True,
        on_delete=fields.NO_ACTION,
    )
    executed_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "transactions"
