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
    def get_by_id(cls, id: int):
        return db.session.query(cls).filter(cls.id == id).first()

    @classmethod
    def all(cls):
        return db.session.query(cls).all()

    def _to_dict(self) -> dict[str, Any]:
        return {}

    def to_dict(self) -> dict[str, Any]:
        d = self._to_dict()

        d.update({"id": self.id})

        return d
