from tortoise import fields
from tortoise.models import Model


class Instrument(Model):
    ticker = fields.CharField(max_length=10, primary_key=True)
    name = fields.CharField(max_length=255)

    class Meta:
        table = "instruments"
