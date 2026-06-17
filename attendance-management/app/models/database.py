import locale
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import get_settings

try:
    locale.setlocale(locale.LC_ALL, 'Chinese (Simplified)_China.936')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'chs')
    except:
        pass

settings = get_settings()
db_url = settings.DATABASE_URL

engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
