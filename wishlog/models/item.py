from typing import Any

from sqlalchemy import (Boolean, Column, DateTime, Float, Integer, String,
                        desc, func)

from ..database import db
from ._base_model import BaseModel


class Item(BaseModel):
    __tablename__ = "items"

    title = Column(String, nullable=False)
    old_cost = Column(String, nullable=True)
    cost = Column(Float, nullable=True)
    link = Column(String, nullable=True)
    image_file_path = Column(String, nullable=True)
    claimed = Column(Boolean, default=False)
    claimed_date = Column(DateTime, nullable=True, default=None)
    desire = Column(Integer, nullable=False, default=50)

    orderable = ["id", "title", "cost", "desire"]

    def __init__(self, title, cost, desire, link=None, image_file_path=None):
        self.title = title
        self.cost = cost
        self.desire = desire
        self.link = link
        self.image_file_path = image_file_path

    @classmethod
    def unclaimed(cls):
        return db.session.query(cls).filter(cls.claimed == False).all()

    @classmethod
    def order_by(cls, value, descending=False):
        if value == "desire":
            return super().order_by("desire", descending=True).order_by(cls.title)
        elif value == "title":
            order_by_value = func.lower(cls.title)
            if descending:
                order_by_value = desc(order_by_value)

            return cls.query().order_by(order_by_value)
        else:
            return super().order_by(value, descending)

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
            "desire": self.desire
        }
