import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Data(Base):
    __tablename__ = 'data'
    id = Column(Integer, primary_key=True)
    meta_info = Column(String(512), nullable=True)
    data = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Tag(Base):
    __tablename__ = 'tag'
    name = Column(String(25), primary_key=True)


class TagData(Base):
    __tablename__ = 'tag__data'
    tag = Column(String, ForeignKey("tag.name"))
    data = Column(Integer, ForeignKey("userdata.id"))
