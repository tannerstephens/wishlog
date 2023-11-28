from typing import Any

from sqlalchemy import Boolean, Column, DateTime, String

from ..database import db
from ._base_model import BaseModel


class Item(BaseModel):
    __tablename__ = "items"

    title = Column(String, nullable=False)
    cost = Column(String, nullable=True)
    link = Column(String, nullable=True)
    image_file_path = Column(String, nullable=True)
    claimed = Column(Boolean, default=False)
    claimed_date = Column(DateTime, nullable=True, default=None)

    def __init__(self, title, cost=None, link=None, image_file_path=None):
        self.title = title
        self.cost = cost
        self.link = link
        self.image_file_path = image_file_path

    @classmethod
    def unclaimed(cls):
        return db.session.query(cls).filter(cls.claimed == False).all()

    def _to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "cost": self.cost,
            "link": self.link,
            "image": f"/images/{self.image_file_path}"
            if self.image_file_path
            else None,
            "claimed": self.claimed,
            "claimed_date": self.claimed_date,
        }
