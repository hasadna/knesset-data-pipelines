from datapackage_pipelines.wrapper import ingest, spew
import logging, time, os
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError


parameters, datapackage, resources = ingest()


def get_engine():
    engine = parameters.get('engine', 'env://DPP_DB_ENGINE')
    if engine.startswith('env://'):
        env_var = engine[6:]
        engine = os.environ.get(env_var)
        assert engine is not None, \
            "Couldn't connect to DB - " \
            "Please set your '%s' environment variable" % env_var
    engine = create_engine(engine)
    try:
        engine.connect()
    except OperationalError:
        logging.exception('Failed to connect to database %s', engine)
        raise
    return engine


def get_resources():
    for resource in resources:
        yield resource
    logging.info('renaming sql table {} --> {}'.format(parameters['temp-table'], parameters['table']))
    engine = get_engine()
    connection = engine.connect()
    try:
        connection.execute('drop table "{}"'.format(parameters['table']))
    except Exception:
        pass
    connection.execute('alter table "{}" rename to "{}"'.format(parameters['temp-table'], parameters['table']))
    connection.close()


spew(datapackage, get_resources())
