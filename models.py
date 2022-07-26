from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Float, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base  = declarative_base()

class Glossary(Base):
    __tablename__ = 'glossary'
    id  = Column(Integer, primary_key=True, index=True)
    src_lang = Column(String)
    tgt_lang = Column(String)
    src_term = Column(String)
    tgt_term = Column(String)
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    time_updated = Column(DateTime(timezone=True), onupdate=func.now())
    transcript_id = Column(Integer, ForeignKey('transcript.id'))

    transcript = relationship('Transcript')


class Transcript(Base):
    __tablename__ = 'transcript'
    id = Column(Integer, primary_key=True)
    src_text = Column(String)
    tgt_text = Column(String)
    src_lang = Column(String)
    tgt_lang = Column(String)
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    time_updated = Column(DateTime(timezone=True), onupdate=func.now())
    meeting_id = Column(Integer, ForeignKey('meeting.id'))
    
    meeting = relationship('Meeting')


class Meeting(Base):
    __tablename__ = 'meeting'
    id = Column(Integer, primary_key=True)
    title = Column(String)
    description = Column(String)
    time_created = Column(DateTime(timezone=True), server_default=func.now())
    time_updated = Column(DateTime(timezone=True), onupdate=func.now())