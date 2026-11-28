""" This files purpose is to initaite the SQLAlchemy engine and session setup, plus the connection string"""
import os
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()
password = os.getenv("DB_PASSWORD")
if password is None:
    raise RuntimeError("DB_PASSWORD is not set. Add a line DB_PASSWORD=your-mysql-root-password to .env")

# URL.create escapes the password, so characters like @ : / # % don't break the connection string.
DATABASE_URL = URL.create(
    drivername="mysql+pymysql",
    username="root",
    password=password,
    host="127.0.0.1",
    port=3306,
    database="biotech_catalyst",
)

engine = create_engine(DATABASE_URL, echo=True)

SESSION_LOCAL = sessionmaker(bind=engine)
