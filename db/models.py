from .database import Base
from sqlalchemy import Column, Integer, String, Boolean


class UserEntity(Base):
    __tablename__ = "avatars_ai_users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    user_email = Column(String)
    is_pro = Column(Boolean, default=False)
    access_count = Column(Integer)