from typing import List
from sqlalchemy import ForeignKey,String
from sqlalchemy import DateTime,DECIMAL,BigInteger
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
from datetime import datetime, timezone


class Base(DeclarativeBase):
    "Base class for tables, i'll explain what it does below"
    
    
class Companies(Base):
    "Represents each company we plan on modeling biotech and financial data for "
    __tablename__ = "companies"
    company_id : Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50),unique = True)
    ticker : Mapped[str] = mapped_column(String(30))
    cik : Mapped[str] = mapped_column(String(10), unique=True)
    
class CompanyAliases(Base):
    " This table allows us to sidestep a alias naming issue and insure the scripts assign the correct data to the correct tables"
    alias_id : Mapped[int] = mapped_column(primary_key=True)
    alias_name : Mapped[str] = mapped_column(String(50),unique= True)
    company_id: Mapped[int] = mapped_column(ForeignKey("Companies.company_id"),unique=True)
    source: Mapped[str] = mapped_column(String(50))
    
class Securities(Base):
    security_id : Mapped[int] = mapped_column(primary_key=True)
    ticker : Mapped[str] = mapped_column(ForeignKey("Companies.ticker"))
    company_id : Mapped[str] = mapped_column(ForeignKey("Companies.company_id"),unique=True,nullable=True)
    type : Mapped[str] = mapped_column(String(30))
    
class Prices(Base):
    security_id : Mapped[int] = mapped_column(ForeignKey("Securities.security_id"),unique=True,primary_key=True)
    trade_date : Mapped[datetime] = mapped_column(DateTime,primary_key=True)
    ticker : Mapped[str] = mapped_column(ForeignKey("Companies.ticker"))
    close : Mapped[float] = mapped_column(DECIMAL(12,4))
    adjusted_close : Mapped[float] = mapped_column(DECIMAL(12,4))
    volumne: Mapped[int] = mapped_column(BigInteger)
    

    
     
    