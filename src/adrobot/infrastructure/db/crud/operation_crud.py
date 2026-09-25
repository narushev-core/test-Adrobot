from __future__ import annotations

from adrobot.infrastructure.db.base import Base
from adrobot.infrastructure.db.crud.base import CRUDBase


class OperationCRUD[T: Base](CRUDBase[T]): ...
