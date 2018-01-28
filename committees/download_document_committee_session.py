from datapackage_pipelines.wrapper import ingest, spew
import logging, os, requests
from datapackage_pipelines_knesset.retry_get_response_content import get_retry_response_content
from copy import deepcopy


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
        all_blobs.setdefault(file_row["document_committee_session_id"], []).append(file_row)
else:
    rows_schema = datapackage["resources"][0]

all_rows = {}
for row in rows_resource:
    all_rows.setdefault(int(row["DocumentCommitteeSessionID"]), []).append(row)

download_rows = []
verify_rows = []
for document_committee_session_id, rows in all_rows.items():
    blobs = all_blobs.get(document_committee_session_id)
    for row in rows:
        if blobs:
            has_blob = False
            for blob_row in blobs:
                if blob_row["group_type_id"] == row["GroupTypeID"] and blob_row["application_desc"] == row["ApplicationDesc"]:
                    has_blob = True
                    break
            if has_blob:
                verify_rows.append(row)
            else:
                download_rows.append(row)
        else:
            download_rows.append(row)

logging.info("{} download rows, {} verify rows".format(len(download_rows), len(verify_rows)))


def get_resource():
    for action, row in [("download", row) for row in download_rows]:  #  + [("verify", row) for row in verify_rows]:
        try:
            rel_filename = os.path.join("files", str(row["GroupTypeID"]),
                                        str(row["DocumentCommitteeSessionID"])[0],
                                        str(row["DocumentCommitteeSessionID"])[1],
                                        str(row["DocumentCommitteeSessionID"]) + "." + row["ApplicationDesc"])
            if not files_limit or stats["downloaded files"]:
                content = get_retry_response_content(row["FilePath"], None, None, None, retry_num=1, num_retries=10,
                                                     seconds_between_retries=10,
                                                     skip_not_found_errors=skip_not_found_errors)
                filename = os.path.join(out_path, rel_filename)
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, "wb") as f:
                    f.write(content)
                stats["downloaded files"] += 1
            row.update(filename=rel_filename)
            yield row
        except Exception as e:
            logging.exception("failed to parse CommitteeSessionID {}".format(row["CommitteeSessionID"]))
            row.update(error=str(e))
            errors.append(row)
            # if len(errors) > 1000:
            #     raise Exception("Too many errors!")


def get_errors_resource():
    for error in errors:
        yield error


def get_resources():
    yield get_resource()
    yield get_errors_resource()


datapackage["resources"] = [rows_schema, deepcopy(rows_schema)]
datapackage["resources"][0]["schema"]["fields"].append({"name": "filename", "type": "string"})
datapackage["resources"][1].update(name="errors", path="errors.csv")
datapackage["resources"][1]["schema"]["fields"] += [{"name": "error", "type": "string"}]


spew(datapackage, get_resources(), stats)
