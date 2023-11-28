from typing import Any

from sqlalchemy import Column, Integer

from ..database import db


class BaseModel(db.Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)

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
    @property
    def query(cls):
        return db.session.query(cls)

    @classmethod
    def get_by_id(cls, id: int):
        return cls.query.filter(cls.id == id).first()

    @classmethod
    def all(cls):
        return cls.query.all()

    @classmethod
    def filter(cls, *args):
        return cls.query.filter(*args)

    @classmethod
    def filter_by(cls, **kwargs):
        return cls.query.filter_by(**kwargs)

    @classmethod
    def order_by(cls, first, *args):
        return cls.query.order_by(first, *args)

    def _to_dict(self) -> dict[str, Any]:
        return {}

    def to_dict(self) -> dict[str, Any]:
        d = self._to_dict()

        d.update({"id": self.id})

        return d
