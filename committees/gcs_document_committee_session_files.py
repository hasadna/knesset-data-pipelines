from datapackage_pipelines.wrapper import ingest, spew
import logging, os, requests
from datapackage_pipelines_knesset.retry_get_response_content import get_retry_response_content
from copy import deepcopy
from google.cloud import storage
import regex
from datapackage_pipelines.utilities.resources import PROP_STREAMING


parameters, datapackage, resources = ingest()
stats = {"matching files": 0, "invalid files": 0}


storage_client = None
all_blobs = {}
if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or not os.path.exists(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]):
    raise Exception("integration with google storage is required, environment variable GOOGLE_APPLICATION_CREDENTIALS must point to a google credentials json file")


def get_resource():
    logging.info("Listing all existing blobs from google storage")
    storage_client = storage.Client()
    storage_bucket = storage_client.bucket(os.environ.get("KNESSET_DATA_PIPELINES_BUCKET", "knesset-data-pipelines"))
    for blob in storage_bucket.list_blobs(prefix="data/committees/download_document_committee_session/files"):
        re_match = regex.match("data/committees/download_document_committee_session/files/"
                               "([0-9]*)/([0-9]*)/([0-9]*)/([0-9]*)\.(.*)", blob.name)
        if re_match:
            group_type_id, _, _, document_committee_session_id, application_desc = re_match.groups()
            group_type_id, document_committee_session_id = int(group_type_id), int(document_committee_session_id)
            yield {"document_committee_session_id": document_committee_session_id,
                   "group_type_id": group_type_id,
                   "application_desc": application_desc,
                   "name": blob.name,
                   "size": blob.size}
            stats["matching files"] += 1
        else:
            logging.warning("Invalid file: {}".format(blob.name))
            stats["invalid files"] += 1


datapackage["resources"] = [{PROP_STREAMING: True,
                             "name": "files",
                             "path": "files.csv",
                             "schema": {"fields": [{"name": "document_committee_session_id", "type": "integer"},
                                                   {"name": "group_type_id", "type": "integer"},
                                                   {"name": "application_desc", "type": "string"},
                                                   {"name": "name", "type": "string"},
                                                   {"name": "size", "type": "integer"}]}}]


spew(datapackage, [get_resource()], stats)
