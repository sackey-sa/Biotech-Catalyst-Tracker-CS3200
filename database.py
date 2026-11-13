""" This files purpose is to initaite the SQLAlchemy engine and session setup, plus the connection string"""
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker 

load_dotenv()
password = os.getenv("DB_PASSWORD")

engine = create_engine(f"mysql+pymysql://root:{password}@127.0.0.1:3306/biotech_catalyst",echo=True)

SESSION_LOCAL = sessionmaker(bind=engine)
