from datetime import datetime


class AbstractBaseEntity:
    def __init__(self) -> None:
        self.id: str = ""
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()
