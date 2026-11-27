"""Shared lookups: the company seed list, alias mapping, and drug de-duplication."""
import csv
import logging
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Companies, CompanyAliases, Drugs, Securities
from pipeline import config
from pipeline.normalize import clip, fold

log = logging.getLogger(__name__)


@dataclass
class SeedCompany:
    """One row of data/companies.csv."""
    ticker: str
    name: str
    ctgov_sponsors: list[str] = field(default_factory=list)
    openfda_prefixes: list[str] = field(default_factory=list)


def _split(cell: str | None) -> list[str]:
    return [p.strip() for p in (cell or "").split("|") if p.strip()]


def read_seed_companies() -> list[SeedCompany]:
    with open(config.COMPANIES_CSV, newline="", encoding="utf-8") as f:
        return [SeedCompany(ticker=r["ticker"].strip().upper(), name=r["name"].strip(),
                            ctgov_sponsors=_split(r.get("ctgov_sponsors")),
                            openfda_prefixes=_split(r.get("openfda_prefixes")))
                for r in csv.DictReader(f) if r.get("ticker", "").strip()]


def company_ids_by_ticker(session: Session) -> dict[str, int]:
    """{'VRTX': 1, ...} for company stocks already in securities."""
    rows = session.execute(select(Securities.ticker, Securities.company_id)
                           .where(Securities.company_id.is_not(None)))
    return {t.upper(): cid for t, cid in rows}


class AliasRegistry:
    """Records every spelling of a company name seen in a source.

    alias_name is unique and MySQL compares it case-insensitively, so lookups use fold().
    """

    def __init__(self, session: Session):
        self.session = session
        self.by_name = {fold(a.alias_name): a.company_id
                        for a in session.scalars(select(CompanyAliases))}

    def company_for(self, name: str | None) -> int | None:
        return self.by_name.get(fold(name)) if name else None

    def add(self, name: str | None, company_id: int, source: str) -> None:
        name = clip(name, 250)
        if not name:
            return
        existing = self.by_name.get(fold(name))
        if existing is None:
            self.session.add(CompanyAliases(alias_name=name, company_id=company_id, source=source))
            self.by_name[fold(name)] = company_id
        elif existing != company_id:
            log.warning("Alias %r already maps to company %s; not remapping to %s",
                        name, existing, company_id)


class DrugRegistry:
    """Reuses drug rows across trials and FDA applications.

    drugs has no unique key, so we de-duplicate here: an FDA drug matches an existing row
    with the same ingredient (and fills in its brand); a trial intervention name matches
    an existing brand name or ingredient before a new row is created.
    """

    def __init__(self, session: Session):
        self.session = session
        self.by_pair: dict[tuple[str, str], Drugs] = {}
        self.by_brand: dict[str, Drugs] = {}
        self.by_ingredient: dict[str, Drugs] = {}
        for d in session.scalars(select(Drugs)):
            self._index(d)

    def _index(self, d: Drugs) -> None:
        self.by_pair[(fold(d.brand_name or ""), fold(d.active_ingredient))] = d
        if d.brand_name:
            self.by_brand.setdefault(fold(d.brand_name), d)
        self.by_ingredient.setdefault(fold(d.active_ingredient), d)

    def _create(self, brand: str | None, ingredient: str) -> Drugs:
        d = Drugs(brand_name=brand, active_ingredient=ingredient)
        self.session.add(d)
        self.session.flush()  # assign drug_id
        self._index(d)
        return d

    def for_trial(self, intervention: str) -> int | None:
        name = clip(intervention, 255)
        if not name:
            return None
        d = self.by_brand.get(fold(name)) or self.by_ingredient.get(fold(name))
        return (d or self._create(None, name)).drug_id

    def for_fda(self, brand: str | None, ingredient: str) -> int:
        brand, ingredient = clip(brand, 255), clip(ingredient, 255) or "UNKNOWN"
        d = self.by_pair.get((fold(brand or ""), fold(ingredient)))
        if d is None:
            d = self.by_ingredient.get(fold(ingredient))
            if d is not None and d.brand_name is None and brand:
                d.brand_name = brand        # trial drug now has an approved brand name
                self._index(d)
            elif d is None or (brand and d.brand_name and fold(d.brand_name) != fold(brand)):
                d = self._create(brand, ingredient)
        return d.drug_id


def get_companies(session: Session) -> dict[int, Companies]:
    return {c.company_id: c for c in session.scalars(select(Companies))}
