"""Defines every table in the Biotech Catalyst Tracker database (schema blueprint only)."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (BigInteger, CheckConstraint, DECIMAL, Date, DateTime,
                        ForeignKey, String)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Parent class for all tables; collects their metadata for create_all."""


class Companies(Base):
    """One row per public company. Ticker lives in securities, not here."""
    __tablename__ = "companies"
    company_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(250), unique=True)
    cik: Mapped[str] = mapped_column(String(10), unique=True)


class CompanyAliases(Base):
    """Maps each source's spelling of a company name to one company_id."""
    __tablename__ = "company_aliases"
    alias_id: Mapped[int] = mapped_column(primary_key=True)
    alias_name: Mapped[str] = mapped_column(String(250), unique=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.company_id"))
    source: Mapped[str] = mapped_column(String(50))


class Securities(Base):
    """Anything with a price: company stocks plus benchmarks like XBI (company_id NULL)."""
    __tablename__ = "securities"
    security_id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String(50), unique=True)
    company_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("companies.company_id"), unique=True)
    type: Mapped[str] = mapped_column(String(30))


class Prices(Base):
    """One row per security per trading day."""
    __tablename__ = "prices"
    security_id: Mapped[int] = mapped_column(
        ForeignKey("securities.security_id"), primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    close: Mapped[Decimal] = mapped_column(DECIMAL(12, 4))
    adjusted_close: Mapped[Decimal] = mapped_column(DECIMAL(12, 4))
    volume: Mapped[int] = mapped_column(BigInteger)


class Drugs(Base):
    """One row per drug product."""
    __tablename__ = "drugs"
    drug_id: Mapped[int] = mapped_column(primary_key=True)
    brand_name: Mapped[Optional[str]] = mapped_column(String(255))  # trial drugs often have none
    active_ingredient: Mapped[str] = mapped_column(String(255))


class Conditions(Base):
    """Diseases studied in trials; names are unique so loaders can reuse rows."""
    __tablename__ = "conditions"
    condition_id: Mapped[int] = mapped_column(primary_key=True)
    condition_name: Mapped[str] = mapped_column(String(255), unique=True)


class Trials(Base):
    """One row per clinical trial from ClinicalTrials.gov."""
    __tablename__ = "trials"
    nct_number: Mapped[str] = mapped_column(String(40), primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.company_id"))
    phase: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(40))
    enrollment: Mapped[Optional[int]]
    start_date: Mapped[Optional[date]] = mapped_column(Date)
    completion_date: Mapped[Optional[date]] = mapped_column(Date)


class TrialConditions(Base):
    """Join table: a trial studies many conditions; a condition appears in many trials."""
    __tablename__ = "trial_conditions"
    nct_number: Mapped[str] = mapped_column(
        String(40), ForeignKey("trials.nct_number"), primary_key=True)
    condition_id: Mapped[int] = mapped_column(
        ForeignKey("conditions.condition_id"), primary_key=True)


class TrialDrugs(Base):
    """Join table: a trial tests many drugs; a drug appears in many trials."""
    __tablename__ = "trial_drugs"
    nct_number: Mapped[str] = mapped_column(
        String(40), ForeignKey("trials.nct_number"), primary_key=True)
    drug_id: Mapped[int] = mapped_column(
        ForeignKey("drugs.drug_id"), primary_key=True)


class FdaActions(Base):
    """One row per original FDA application (no supplements) from openFDA."""
    __tablename__ = "fda_actions"
    fda_action_id: Mapped[int] = mapped_column(primary_key=True)
    application_number: Mapped[str] = mapped_column(String(50), unique=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.company_id"))
    drug_id: Mapped[int] = mapped_column(ForeignKey("drugs.drug_id"))
    submission_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    action_date: Mapped[date] = mapped_column(Date)


class Filings(Base):
    """One row per SEC filing (mainly 8-Ks) from EDGAR."""
    __tablename__ = "filings"
    accession_number: Mapped[str] = mapped_column(String(50), primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.company_id"))
    form_type: Mapped[str] = mapped_column(String(50))
    filing_date: Mapped[date] = mapped_column(Date)
    acceptance_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime)  # UTC


class Events(Base):
    """Derived table: one row per trial readout or FDA decision being analyzed.

    Subject (what it's about): at most one of nct_number or fda_action_id.
    Evidence (where it came from): accession_number and/or source_url.
    An openFDA action counts as its own evidence.
    """
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint(
            "(nct_number IS NOT NULL) + (fda_action_id IS NOT NULL) <= 1",
            name="at_most_one_subject"),
        CheckConstraint(
            "accession_number IS NOT NULL OR source_url IS NOT NULL"
            " OR fda_action_id IS NOT NULL",
            name="has_evidence"),
    )
    event_id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.company_id"))
    event_type: Mapped[str] = mapped_column(String(50))  # fda_decision or trial_readout
    outcome: Mapped[str] = mapped_column(String(30))  # approved, rejected, positive, negative, mixed
    event_timestamp: Mapped[datetime] = mapped_column(DateTime)  # UTC
    trading_day: Mapped[date] = mapped_column(Date)
    # Keep these three FKs without ON DELETE rules: MySQL rejects CHECKs on
    # columns whose FK has SET NULL or CASCADE.
    nct_number: Mapped[Optional[str]] = mapped_column(
        String(40), ForeignKey("trials.nct_number"))
    fda_action_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("fda_actions.fda_action_id"))
    accession_number: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("filings.accession_number"))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))