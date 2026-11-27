""" This files purpose is to initaite the SQLAlchemy engine and session setup, plus the connection string"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()
password = os.getenv("DB_PASSWORD")

# DATABASE_URL lets you point at a different database (e.g. sqlite:///test.db for testing).
DATABASE_URL = os.getenv("DATABASE_URL") or f"mysql+pymysql://root:{password}@127.0.0.1:3306/biotech_catalyst"

engine = create_engine(DATABASE_URL, echo=True)

SESSION_LOCAL = sessionmaker(bind=engine)
