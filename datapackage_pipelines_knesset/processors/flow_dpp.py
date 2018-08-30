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

module, chdir_path = parameters['module'], parameters.get('chdir', '..')

logging.info('running flow module {} from directory {}'.format(module, chdir_path))
with redirect_stderr(StderrWriter()):
    with redirect_stdout(StdoutWriter()):
        os.chdir(chdir_path)
        import_module(module).flow().process()

spew(datapackage, resources)
