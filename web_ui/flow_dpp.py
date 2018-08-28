from datapackage_pipelines.wrapper import ingest, spew
import logging, sh, os, sys
from contextlib import redirect_stderr, redirect_stdout
from web_ui.flow import flow


class StdoutWriter:

    def write(self, message):
        logging.info(message)

    def flush(self):
        pass


class StderrWriter:

    def write(self, message):
        logging.error(message)

    def flush(self):
        pass


parameters, datapackage, resources = ingest()


def finalizer():
    with redirect_stderr(StderrWriter()):
        with redirect_stdout(StdoutWriter()):
            os.chdir('..')
            flow().process()


spew(datapackage, resources, finalizer=finalizer)
