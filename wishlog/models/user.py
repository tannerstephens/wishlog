from hashlib import pbkdf2_hmac
from os import urandom

from sqlalchemy import Column, Index, String, func

from ..database import db
from ._base_model import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    def __init__(self, username: str, password: str):
        self.username = username.lower()
        self.password_hash = self.hash_password(password)

    def hash_password(self, password: str, salt: bytes | None = None) -> bytes:
        if salt is None:
            salt = urandom(32)

        key = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        return salt + key

    def check_password(self, password: str) -> bool:
        salt = self.password_hash[:32]

        return self.hash_password(password, salt) == self.password_hash

    @classmethod
    def get_by_uername(cls, username: str):
        return (
            db.session.query(cls)
            .filter(func.lower(cls.username) == username.lower())
            .first()
        )


user_username_index = Index("user_username_idx", func.lower(User.username), unique=True)
