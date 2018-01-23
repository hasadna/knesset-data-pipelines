from datapackage_pipelines.wrapper import spew, ingest
import time, logging, datetime


DEFAULT_SLEEP_SECONDS = .01
DEFAULT_LOG_INTERVAL_SECONDS = 900
DEFAULT_ROWS_PER_PAGE = 1


def filter_resource(resource, sleep_seconds, start_time, log_interval_seconds, rows_per_page):
    last_log_seconds = 0
    for i, row in enumerate(resource):
        yield row
        elapsed_seconds = (datetime.datetime.now()-start_time).total_seconds()
        seconds_since_last_log = elapsed_seconds - last_log_seconds
        if seconds_since_last_log > log_interval_seconds:
            last_log_seconds = elapsed_seconds
            processed_what = "{} rows".format(i)
            if rows_per_page > 1:
                processed_what += " {} pages".format(int(i/rows_per_page))
            logging.info("processed {}, elapsed time (seconds)={}".format(processed_what, elapsed_seconds))
        if rows_per_page == 1 or (i > 0 and i % rows_per_page == 0):
            time.sleep(sleep_seconds)


def filter_resources(datapackage, resources, parameters):
    input_resource_name = parameters.get("resource")
    sleep_seconds = float(parameters.get("sleep-seconds", DEFAULT_SLEEP_SECONDS))  # sleep between rows
    log_interval_seconds = int(parameters.get("log-interval-seconds", DEFAULT_LOG_INTERVAL_SECONDS))  # log progress every X seconds
    rows_per_page = int(parameters.get("rows-per-page", DEFAULT_ROWS_PER_PAGE))
    start_time = datetime.datetime.now()
    for resource_descriptor, resource in zip(datapackage["resources"], resources):
        if not input_resource_name or input_resource_name == resource_descriptor["name"]:
            logging.info("throttling resource {}: sleep_seconds={}".format(resource_descriptor["name"],
                                                                           sleep_seconds))
            yield filter_resource(resource, sleep_seconds, start_time, log_interval_seconds, rows_per_page)
        else:
            yield resource


parameters, datapackage, resources = ingest()
spew(datapackage, filter_resources(datapackage, resources, parameters))
