#This is db.py
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, JSON, Text
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine("sqlite:///vrtta.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()

class ProductScore(Base):
    __tablename__ = "product_scores"
    id = Column(Integer, primary_key=True)
    product_name = Column(String(255), nullable=False)
    materials = Column(JSON, default=list)          # list[str]
    weight_grams = Column(Float)
    transport = Column(String(64))
    packaging = Column(String(128))
    gwp = Column(Float)
    cost = Column(Float)
    circularity = Column(Float)
    sustainability_score = Column(Float)
    rating = Column(String(2))
    suggestions = Column(JSON, default=list)        # list[str]
    raw_payload = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(engine)

