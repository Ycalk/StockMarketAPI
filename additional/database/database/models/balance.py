from tortoise import fields
from tortoise.models import Model
from .user import User
from .instrument import Instrument


class Balance(Model):
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="balances", on_delete=fields.CASCADE
    )
    instrument: fields.ForeignKeyRelation["Instrument"] = fields.ForeignKeyField(
        "models.Instrument", related_name="balances", on_delete=fields.CASCADE
    )
    amount = fields.IntField()

    class Meta:
        table = "balances"
        unique_together = (("user", "instrument"),)
