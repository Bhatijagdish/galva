import asyncio
import os
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from lib import setup_logger

load_dotenv()

DATABASE_CONNECTION_ATTEMPTS = 10
DATABASE_CONNECTION_TIMEOUT = 2

DATABASE_TYPE = os.getenv("DBTYPE", default="sqlite")

APP_DIR = os.path.dirname(os.path.dirname(__file__))

logger = setup_logger()

if DATABASE_TYPE == "postgres":
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", default="localhost")
    POSTGRES_DB = os.getenv("POSTGRES_DB", default="peptaloid")
    POSTGRES_USER = os.getenv("POSTGRES_USER", default="user")
    POSTGRES_PASS = os.getenv("POSTGRES_PASS", default="password")
    POSTGRES_PORT = os.getenv("POSTGRES_PORT", default="5432")
    DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    db_engine = create_engine(
        DATABASE_URL,
        echo=True,
        connect_args={"connect_timeout": DATABASE_CONNECTION_TIMEOUT}
    )

else:
    DB_ABS_PATH = os.path.join(APP_DIR, os.getenv('SQLITE_DB_NAME', "demo_test.db"))
    DATABASE_URL = f"sqlite:///{DB_ABS_PATH}"
    db_engine = create_engine(DATABASE_URL)

Session = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=db_engine
)

Base = declarative_base()


def db_connection() -> Session:
    """This function creates a connection with the database."""
    db = Session()
    try:
        yield db
    finally:
        db.close()


async def initialize_db() -> None:
    """Connect with the database for the first time. This is with the startup of the server."""
    database_alive = False
    attempt = 1

    while not database_alive:
        try:
            try:
                logger.info("Initializing tables creation")
                Base.metadata.create_all(bind=db_engine)
                logger.info("Tables created successfully")
            except (IntegrityError, ProgrammingError):
                pass
            database_alive = True
            logger.info(f"Database connection attempt {attempt} successful")
        except OperationalError:
            logger.info(f"Database connection attempt {attempt} failed (timeout {DATABASE_CONNECTION_TIMEOUT} secs)")
            if attempt == DATABASE_CONNECTION_ATTEMPTS:
                raise ConnectionError("Cannot connect to database")
            attempt += 1
            await asyncio.sleep(DATABASE_CONNECTION_TIMEOUT)
