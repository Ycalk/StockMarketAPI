from tortoise import fields
from tortoise.models import Model
import uuid
import enum
from .user import User
from .instrument import Instrument


class OrderType(str, enum.Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class OrderStatus(str, enum.Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"


class Direction(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"


class Order(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    user: fields.ForeignKeyRelation["User"] = fields.ForeignKeyField(
        "models.User", related_name="orders", on_delete=fields.CASCADE
    )
    type = fields.CharEnumField(OrderType)
    status = fields.CharEnumField(OrderStatus, default=OrderStatus.NEW)
    direction = fields.CharEnumField(Direction)
    instrument: fields.ForeignKeyRelation["Instrument"] = fields.ForeignKeyField(
        "models.Instrument", related_name="orders", on_delete=fields.CASCADE
    )
    quantity = fields.IntField()
    price = fields.IntField(null=True)
    filled = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "orders"
