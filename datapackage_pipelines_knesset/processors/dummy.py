from datapackage_pipelines.wrapper import ingest, spew
import logging, os
from contextlib import redirect_stderr, redirect_stdout
from importlib import import_module


class StdoutWriter:

    def write(self, message):
        message = message.strip()
        if message:
            logging.info(message)

    def flush(self):
        pass


class StderrWriter:

    def write(self, message):
        message = message.strip()
        if (message):
            logging.error(message)

    def flush(self):
        pass


parameters, datapackage, resources = ingest()

logging.info(parameters.get('msg', ''))

spew(datapackage, resources)
