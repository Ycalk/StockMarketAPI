from tortoise import fields
from tortoise.models import Model


class Balance(Model):
    user = fields.ForeignKeyField("models.User", related_name="balances", on_delete=fields.CASCADE)
    instrument = fields.ForeignKeyField("models.Instrument", related_name="balances", on_delete=fields.CASCADE)
    amount = fields.IntField()

    class Meta:
        table = "balances"
        unique_together = (("user", "instrument"),)