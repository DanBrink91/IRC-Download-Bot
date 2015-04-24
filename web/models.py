from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class Anime(Base):
	__tablename__ = "animes"

	id = Column(Integer, primary_key = True)
	title = Column(String(255))
	alternative_titles = Column(String(255))
	current_ep = Column(Integer)
	max_ep = Column(Integer)
	mal_id = Column(Integer)

class Episode(Base):
	__tablename__ = "episodes"

	id = Column(Integer, primary_key = True)
	number = Column(Integer)
	status = Column(Integer)
	series = Column(Integer, ForeignKey('animes.id'))
	botname = Column(String(255))
	packnumber = Column(Integer)
	subgroup = Column(String(255))
	quality = Column(String(255))
	filename = Column(String(255))
	anime = relationship(Anime)

engine = create_engine("sqlite:///../mal_db.db")
