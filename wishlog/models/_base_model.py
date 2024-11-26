from typing import Any

from sqlalchemy import Column, Integer, desc

from ..database import db


class BaseModel(db.Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)
    orderable = ["id"]

    def save(self, commit=True):
        db.session.add(self)
        if commit:
            db.session.commit()
        return self

    def delete(self, commit=True):
        db.session.delete(self)
        if commit:
            db.session.commit()

    @classmethod
    def query(cls):
        return db.session.query(cls)

    @classmethod
    def get_by_id(cls, id: int):
        return cls.query().filter(cls.id == id).first()

    @classmethod
    def all(cls):
        return cls.query().all()

    @classmethod
    def filter(cls, *args):
        return cls.query().filter(*args)

    @classmethod
    def filter_by(cls, **kwargs):
        return cls.query().filter_by(**kwargs)

    @classmethod
    def order_by(cls, value: str, descending=False):
        if value in cls.orderable:
            order_by_value = getattr(cls, value)

            if descending:
                order_by_value = desc(order_by_value)

            return cls.query().order_by(order_by_value)
        return cls.query()

    def _to_dict(self) -> dict[str, Any]:
        return {}

    def to_dict(self) -> dict[str, Any]:
        d = self._to_dict()

        d.update({"id": self.id})

        return d
