from pydantic import BaseModel


class EquipmentOut(BaseModel):
    """Serialized equipment catalog entry returned to the client."""

    id: str
    name: str
