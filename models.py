""" File that defines all the tables we will use in our project"""
from typing import Optional
from datetime import datetime,date
from sqlalchemy import ForeignKey,String
from sqlalchemy import DateTime,DECIMAL,BigInteger,Date,CheckConstraint
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
from database import engine



class Base(DeclarativeBase):
    "Base class for tables, i'll explain what it does below"


class Companies(Base):
    "Represents each company we plan on modeling biotech and financial data for "
    __tablename__ = "companies"
    company_id : Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(250),unique = True)
    ticker : Mapped[str] = mapped_column(String(30))
    cik : Mapped[str] = mapped_column(String(10), unique=True)

class CompanyAliases(Base):
    "Gives each table an alias to avoid duplicate names"
    __tablename__ = "company_aliases"
    alias_id : Mapped[int] = mapped_column(primary_key=True)
    alias_name : Mapped[str] = mapped_column(String(250),unique= True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.company_id"))
    source: Mapped[str] = mapped_column(String(50))

class Securities(Base):
    "Table is meant to represent other tradable objects outside of companies"
    __tablename__ = "securities"
    security_id : Mapped[int] = mapped_column(primary_key=True)
    ticker : Mapped[str] = mapped_column(String(50),unique=True)
    company_id : Mapped[int] = mapped_column(ForeignKey("companies.company_id"),
                                             unique=True,nullable=True)
    type : Mapped[str] = mapped_column(String(30))

class Prices(Base):
    "Table represent the prices that securities are sold at "
    __tablename__ = "prices"
    security_id : Mapped[int] = mapped_column(ForeignKey("securities.security_id"),
                                              primary_key=True)
    trade_date : Mapped[date] = mapped_column(Date,primary_key=True)
    close : Mapped[float] = mapped_column(DECIMAL(12,4))
    adjusted_close : Mapped[float] = mapped_column(DECIMAL(12,4))
    volume: Mapped[int] = mapped_column(BigInteger)

class Drugs(Base):
    "Table represents the drugs that are produces"
    __tablename__ ="drugs"
    drug_id : Mapped[int] = mapped_column(primary_key=True)
    brand_name : Mapped[str] = mapped_column(String(100))
    active_ingredient : Mapped[str] = mapped_column(String(100))


class Conditions(Base):
    "The conditions that are related to the drugs in the database"
    __tablename__ = "conditions"
    condition_id : Mapped[int] = mapped_column(primary_key=True,unique=True)
    condition_name : Mapped[str] = mapped_column(String(100))


class Trials(Base):
    " The clinical trials being held and their current states"
    __tablename__ = "trials"
    nct_number :Mapped[str] = mapped_column(String(40),primary_key=True, unique=True)
    company_id :Mapped[int] = mapped_column(ForeignKey("companies.company_id"))
    phase : Mapped[Optional[str]] = mapped_column(String(50))
    status : Mapped[str] = mapped_column(String(40))
    start_date : Mapped[Optional[date]] = mapped_column(Date)
    completion_date : Mapped[Optional[date]] = mapped_column(Date)

class TrialConditions(Base):
    "IDEK"
    __tablename__ = "trial_conditions"
    nct_number : Mapped[str] = mapped_column(String(40),
                                             ForeignKey("trials.nct_number"),primary_key=True)
    condition_id : Mapped[int] = mapped_column(ForeignKey
                                               ("conditions.condition_id"),primary_key=True)

class TrialDrugs(Base):
    "Join table representing the many to many relationship between trials and drugs"
    __tablename__ = "trial_drugs"
    nct_number : Mapped[str] = mapped_column(String(40),
                                                 ForeignKey("trials.nct_number"),primary_key=True)
    drug_id : Mapped[int] = mapped_column(ForeignKey("drugs.drug_id"))

class FdaActions(Base):
    "FDA actions and announcements, very important table"
    __tablename__ = "fda_actions"
    fda_action_id : Mapped[int] = mapped_column(primary_key=True)
    application_number : Mapped[str] = mapped_column(String(50),unique=True)
    company_id : Mapped[int] = mapped_column(ForeignKey("companies.company_id"))
    drug_id : Mapped[int] = mapped_column(ForeignKey("drugs.drug_id"))
    submission_type : Mapped[str] = mapped_column(String(50))
    status : Mapped[str] = mapped_column(String(50))
    action_date : Mapped[datetime] = mapped_column(DateTime(timezone=True))

class Filings(Base):
    " New filings from companies to fda? "
    __tablename__ = "filings"
    accession_number : Mapped[str] = mapped_column(String(50),primary_key=True)
    company_id : Mapped[int] = mapped_column(ForeignKey("companies.company_id"))
    form_type : Mapped[str] = mapped_column(String(50))
    filing_date : Mapped[datetime] = mapped_column(DateTime(timezone=True))
    acceptance_timestamp : Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

class Events(Base):
    "Financial events, buys sells etc etc "
    __tablename__ = "events"
    __table_args__ = (CheckConstraint(
        "(nct_number IS NOT NULL) + (fda_action_id IS NOT NULL) + (accession_number IS NOT NULL) = 1",
        name="one_source_only"),)
    event_id :Mapped[int] = mapped_column(primary_key=True)
    company_id : Mapped[int] = mapped_column(ForeignKey("companies.company_id"))
    event_type: Mapped[str] = mapped_column(String(50))
    event_timestamp: Mapped[datetime] = mapped_column(DateTime)
    trading_day : Mapped[date] = mapped_column(Date)
    nct_number : Mapped[Optional[str]] = mapped_column(String(40),ForeignKey("trials.nct_number"))
    fda_action_id : Mapped[Optional[int]] = mapped_column(ForeignKey(
        "fda_actions.fda_action_id"))
    accession_number : Mapped[Optional[str]] = mapped_column(String(50),ForeignKey("filings.accession_number"))
    source_url : Mapped[Optional[str]] = mapped_column(String(500))


