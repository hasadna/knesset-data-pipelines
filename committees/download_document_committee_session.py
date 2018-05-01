from datapackage_pipelines.wrapper import ingest, spew
import logging, os, requests, time
from datapackage_pipelines_knesset.retry_get_response_content import get_retry_response_content
from copy import deepcopy
import crcmod, base64


def get_crc32c(filename):
    with open(filename, 'rb') as f:
        crc32c = crcmod.predefined.Crc('crc-32c')
        crc32c.update(f.read())
    return base64.b64encode(crc32c.digest()).decode()


def download_document(row):
    rel_filename = os.path.join("files", str(row["GroupTypeID"]),
                                str(row["DocumentCommitteeSessionID"])[0],
                                str(row["DocumentCommitteeSessionID"])[1],
                                str(row["DocumentCommitteeSessionID"]) + "." + row["ApplicationDesc"])
    content = get_retry_response_content(row["FilePath"], None, None, None, retry_num=1, num_retries=10,
                                         seconds_between_retries=10,
                                         skip_not_found_errors=skip_not_found_errors)
    filename = os.path.join(out_path, rel_filename)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "wb") as f:
        f.write(content)
    return rel_filename, os.path.getsize(filename), get_crc32c(filename)


parameters, datapackage, resources = ingest()
stats = {"downloaded files": 0}
files_limit = os.environ.get("FILES_LIMIT")
if files_limit:
    files_limit = int(files_limit)
out_path = parameters["out-path"]
errors = []
skip_not_found_errors = (os.environ.get("SKIP_NOT_FOUND_ERRORS") != "0")


resources = list(resources)
if len(resources) == 2:
    files_resource, rows_resource = resources
else:
    files_resource, rows_resource = None, resources[0]


storage_client = None
all_blobs = {}
if files_resource:
    rows_schema = datapackage["resources"][1]
    for file_row in files_resource:
        document_id = "{}-{}-{}".format(file_row["group_type_id"],
                                        file_row["document_committee_session_id"],
                                        file_row["application_desc"])
        assert document_id not in all_blobs, "duplicated document id: {}".format(document_id)
        all_blobs[document_id] = file_row
else:
    rows_schema = datapackage["resources"][0]


def get_resource():
    for row in rows_resource:
        row.setdefault('filesize', 0)
        row.setdefault('crc32c', None)
        row.setdefault('error', None)
        document_id = "{}-{}-{}".format(row["GroupTypeID"], row["DocumentCommitteeSessionID"], row["ApplicationDesc"])
        blob = all_blobs.get(document_id)
        if not blob or not blob['size'] or not blob['crc32c'] or row.get('crc32c') != blob['crc32c']:
            try:
                filename, filesize, crc32c = download_document(row)
                row.update(filename=filename, filesize=filesize, crc32c=crc32c, error=None)
                stats["downloaded files"] += 1
            except Exception as e:
                logging.exception('failed to download document id {}'.format(document_id))
                errors.append({'error': str(e)})
                row.update(filesize=None, crc32c=None, error=str(e))
        yield row
        time.sleep(0.01)


def get_errors_resource():
    for error in errors:
        yield error


def get_resources():
    yield get_resource()
    yield get_errors_resource()


datapackage["resources"] = [rows_schema, deepcopy(rows_schema)]
datapackage["resources"][0]["schema"]["fields"] += [{"name": "filename", "type": "string"},
                                                    {"name": "filesize", "type": "integer"},
                                                    {"name": "crc32c", "type": "string"},
                                                    {"name": "error", "type": "string"}]
datapackage["resources"][1].update(name="errors", path="errors.csv")
datapackage["resources"][1]["schema"]["fields"] += [{"name": "error", "type": "string"}]


spew(datapackage, get_resources(), stats)
