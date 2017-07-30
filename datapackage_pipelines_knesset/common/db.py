from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, MetaData
import os, logging

def get_engine(connection_string=None):
    if not connection_string:
        connection_string = os.environ["DPP_DB_ENGINE"]
    if connection_string.startswith("sqlite:///../"):
        relpath = connection_string.replace("sqlite:///../", "")
        abspath = os.path.join(os.path.dirname(__file__), "..", "..", relpath)
        connection_string = "sqlite:///{}".format(abspath)
    return create_engine(connection_string)

def get_session(engine=None, connection_string=None):
    if not engine:
        engine = get_engine(connection_string)
    return sessionmaker(bind=engine)()

def get_connection(session=None, engine=None, connection_string=None):
    if not session:
        session = get_session(engine, connection_string)
    return session.connection()

def get_reflect_metadata(bind=None):
    if not bind:
        bind = get_connection()
    metadata = MetaData(bind=bind)
    metadata.reflect()
    return metadata
