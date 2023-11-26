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
