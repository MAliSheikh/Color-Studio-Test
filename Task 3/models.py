from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()

class PriceComparison(Base):
    __tablename__ = "price_comparisons"

    id = Column(Integer, primary_key=True, index=True)
    search_term = Column(String, index=True)
    product_name = Column(String)
    seller = Column(String)
    price = Column(Float)
    url = Column(String)
    date_scraped = Column(DateTime, default=datetime.utcnow)
