from datapackage_pipelines.wrapper import ingest, spew
import logging, os
from google.cloud import storage
import regex
from datapackage_pipelines.utilities.resources import PROP_STREAMING
from datapackage_pipelines_knesset.processors.load_resource import KnessetResourceLoader


if os.environ.get("LOAD_FROM_RESOURCE"):
    KnessetResourceLoader(url='../data/committees/gcs_list_files/datapackage.json',
                          resource='files')()
    exit()
elif not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or not os.path.exists(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]):
    raise Exception("integration with google storage is required, environment variable GOOGLE_APPLICATION_CREDENTIALS must point to a google credentials json file")


parameters, datapackage, resources = ingest()


stats = {"total matching files": 0, "invalid files": 0, "protocol parts": 0, "protocol texts": 0, "session documents": 0}


protocol_text_regex = "data/committees/meeting_protocols_text/files/([0-9]*)/([0-9]*)/([0-9]*)\.(.*)"
protocol_parts_regex = "data/committees/meeting_protocols_parts/files/([0-9]*)/([0-9]*)/([0-9]*)\.(.*)"
session_documents_regex = "data/committees/download_document_committee_session/files/([0-9]*)/([0-9]*)/([0-9]*)/([0-9]*)\.(.*)"


storage_client = None
all_blobs = {}


def get_row(blob, file_type, **kwargs):
    stats["total matching files"] += 1
    #                1b 10b 50b .5k  1k    5k    10k    20k    50k    100k    1mb      5mb      50mb      100mb      1gb
    for log_size in (1, 10, 50, 500, 1000, 5000, 10000, 20000, 50000, 100000, 1000000, 5000000, 50000000, 100000000, 1000000000):
        if blob.size < log_size:
            stats["files size < {}".format(log_size)] = stats.get("files size < {}".format(log_size), 0) + 1
            break
    if file_type == "text":
        stats["protocol texts"] += 1
    elif file_type == "parts":
        stats["protocol parts"] += 1
    elif file_type == "document":
        stats["session documents"] += 1
        stats["docs type {}".format(kwargs["application_desc"])] = stats.get(
            "docs type {}".format(kwargs["application_desc"]), 0) + 1
        stats["docs group {}".format(kwargs["group_type_id"])] = stats.get(
            "docs group {}".format(kwargs["group_type_id"]), 0) + 1
    else:
        raise Exception("Invalid file type {}".format(file_type))
    return {"file_type": file_type,
            "committee_session_id": kwargs.get("committee_session_id"),
            "document_committee_session_id": kwargs.get("document_committee_session_id"),
            "group_type_id": kwargs.get("group_type_id"),
            "application_desc": kwargs.get("application_desc"),
            "extension": kwargs.get("extension"),
            "name": blob.name, "size": blob.size,
            "crc32c": blob.crc32c}


def get_resource():
    logging.info("Listing all existing blobs from google storage")
    storage_client = storage.Client()
    storage_bucket = storage_client.bucket(os.environ.get("KNESSET_DATA_PIPELINES_BUCKET", "knesset-data-pipelines"))
    prefix = "data/committees/"
    if parameters.get('type') == 'document':
        prefix += 'download_document_committee_session/files/'
    elif parameters.get('type') == 'text':
        prefix += 'meeting_protocols_text/files'
    for blob in storage_bucket.list_blobs(prefix=prefix):
        re_match_text = regex.match(protocol_text_regex, blob.name)
        re_match_parts = regex.match(protocol_parts_regex, blob.name)
        re_match_documents = regex.match(session_documents_regex, blob.name)
        if re_match_text:
            _, _, committee_session_id, extension = re_match_text.groups()
            yield get_row(blob, "text",
                          committee_session_id=int(committee_session_id), extension=extension)
        elif re_match_parts:
            _, _, committee_session_id, extension = re_match_parts.groups()
            yield get_row(blob, "parts",
                          committee_session_id=int(committee_session_id), extension=extension)
        elif re_match_documents:
            group_type_id, _, _, document_committee_session_id, application_desc = re_match_documents.groups()
            yield get_row(blob, "document",
                          document_committee_session_id=int(document_committee_session_id),
                          group_type_id=int(group_type_id), application_desc=application_desc)
        else:
            logging.warning("Invalid file: {}".format(blob.name))
            stats["invalid files"] += 1


def get_stats_resource():
    yield from ({"stat": k, "value": v} for k, v in stats.items())


datapackage["resources"] = [{PROP_STREAMING: True,
                             "name": "files",
                             "path": "files.csv",
                             "schema": {"fields": [{"name": "file_type", "type": "string"},
                                                   {"name": "committee_session_id", "type": "integer"},
                                                   {"name": "document_committee_session_id", "type": "integer"},
                                                   {"name": "group_type_id", "type": "integer"},
                                                   {"name": "application_desc", "type": "string"},
                                                   {"name": "extension", "type": "string"},
                                                   {"name": "name", "type": "string"},
                                                   {"name": "size", "type": "integer"},
                                                   {"name": "crc32c", "type": "string"},]}},]

output_resources = [get_resource()]

if not parameters.get('type'):
    output_resources.append(get_stats_resource())
    datapackage["resources"].append({PROP_STREAMING: True,
                                     "name": "stats",
                                     "path": "stats.csv",
                                     "schema": {"fields": [{"name": "stat", "type": "string"},
                                                           {"name": "value", "type": "integer"}]}})





spew(datapackage, output_resources, stats)
