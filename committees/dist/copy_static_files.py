from datapackage_pipelines.wrapper import ingest, spew
import subprocess, logging


def copy_static_files():
    logging.info("Copying static files from ./static to ./dist/static")
    subprocess.check_call(["mkdir", "-p", "../../data/committees/dist/dist"])
    subprocess.check_call(["cp", "-rf", "static", "../../data/committees/dist/dist/"])


parameters, datapackage, resources = ingest()
spew(datapackage, [], finalizer=copy_static_files)
