from sqlmodel import SQLModel, Session, create_engine
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL, 
    pool_size=5,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=1800,
    pool_pre_ping=True,
    echo=True
)

def create_db_and_Tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session