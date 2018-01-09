from datapackage_pipelines.wrapper import ingest, spew
import logging, os, requests
from datapackage_pipelines_knesset.retry_get_response_content import get_retry_response_content


parameters, datapackage, resources = ingest()
stats = {"downloaded files": 0}
check_remote_storage = os.environ.get("CHECK_REMOTE_STORAGE", parameters.get("check-remote-storage"))
files_limit = int(os.environ.get("FILES_LIMIT", parameters.get("files-limit", "50")))
out_path = parameters["out-path"]


def file_exists(rel_filename):
    if check_remote_storage:
        url = check_remote_storage + rel_filename
        return requests.head(url).status_code == 200
    else:
        return None


def get_resource(resource):
    for row in resource:
        if stats["downloaded files"] < files_limit:
            rel_filename = os.path.join("files", str(row["GroupTypeID"]),
                                   str(row["DocumentCommitteeSessionID"])[0],
                                   str(row["DocumentCommitteeSessionID"])[1],
                                   str(row["DocumentCommitteeSessionID"]) + "." + row["ApplicationDesc"])
            if not file_exists(rel_filename):
                content = get_retry_response_content(row["FilePath"], None, None, None, retry_num=1, num_retries=10,
                                                     seconds_between_retries=10)
                filename = os.path.join(out_path, rel_filename)
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                with open(filename, "wb") as f:
                    f.write(content)
                stats["downloaded files"] += 1
                row["filename"] = rel_filename
                yield row


def get_resources():
    for resource in resources:
        yield get_resource(resource)


datapackage["resources"][0]["schema"]["fields"].append({"name": "filename", "type": "string"})


spew(datapackage, get_resources(), stats)
