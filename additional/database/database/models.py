from tortoise import fields
from tortoise.models import Model
import enum
import uuid


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class User(Model):
    id = fields.UUIDField(pk=True, default=uuid.uuid4)
    name = fields.CharField(max_length=100)
    role = fields.CharEnumField(UserRole, default=UserRole.USER)
    created_at = fields.DatetimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name