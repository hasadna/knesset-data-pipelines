from datapackage_pipelines.wrapper import ingest, spew
import logging, os, requests, csv, shutil
from knesset_data.protocols.committee import CommitteeMeetingProtocol
from copy import deepcopy
from datapackage_pipelines_knesset.common import utils


parameters, datapackage, resources = ingest()
stats = {"parsed files": 0}
check_remote_storage = os.environ.get("CHECK_REMOTE_STORAGE", parameters.get("check-remote-storage"))
files_limit = os.environ.get("FILES_LIMIT")
if files_limit:
    files_limit = int(files_limit)
out_path = parameters["out-path"]
download_from_path = parameters.get("download-from-path")
download_from_remote_storage = parameters.get("download-from-remote-storage")
parse_type = parameters["type"]
errors = []


resources = list(resources)
if len(resources) == 2:
    files_resource, rows_resource = resources
else:
    files_resource, rows_resource = None, resources[0]


all_blobs = {}
if files_resource:
    rows_schema = datapackage["resources"][1]
    for file_row in files_resource:
        all_blobs.setdefault(file_row["committee_session_id"], []).append(file_row)
else:
    rows_schema = datapackage["resources"][0]

all_rows = {}
for row in rows_resource:
    all_rows.setdefault(int(row["CommitteeSessionID"]), []).append(row)


download_rows = []
verify_rows = []
for committee_session_id, rows in all_rows.items():
    blobs = all_blobs.get(committee_session_id)
    for row in rows:
        if blobs:
            has_blob = False
            for blob_row in blobs:
                if blob_row["committee_session_id"] == row["CommitteeSessionID"]:
                    has_blob = True
                    break
            if has_blob:
                verify_rows.append(row)
            else:
                download_rows.append(row)
        else:
            download_rows.append(row)


def parse_protocol(output_filename, protocol):
    full_output_filename = out_path + "/" + output_filename
    os.makedirs(os.path.dirname(full_output_filename), exist_ok=True)
    if parse_type == "text":
        with open(full_output_filename, "w") as of:
            of.write(protocol.text)
            stats["parsed files"] += 1
    elif parse_type == "parts":
        with utils.temp_file() as filename:
            with open(filename, "w") as f:
                csv_writer = csv.writer(f)
                csv_writer.writerow(["header", "body"])
                for part in protocol.parts:
                    csv_writer.writerow([part.header, part.body])
            shutil.copy(filename, full_output_filename)
            stats["parsed files"] += 1
    else:
        raise NotImplementedError


def get_resource():
    for row_num, row in enumerate(download_rows):
        logging.info("{} / {}".format(row_num, len(download_rows)))
        try:
            original_filename = os.path.join("files", str(row["GroupTypeID"]),
                                             str(row["DocumentCommitteeSessionID"])[0],
                                             str(row["DocumentCommitteeSessionID"])[1],
                                             str(row["DocumentCommitteeSessionID"]) + "." + row["ApplicationDesc"])
            ext = os.path.splitext(original_filename)[1].lower()
            output_filename = "files/{}/{}/{}.{}".format(str(row["CommitteeSessionID"])[0],
                                                         str(row["CommitteeSessionID"])[1],
                                                         str(row["CommitteeSessionID"]),
                                                         "csv" if parse_type == "parts" else "txt")
            if not files_limit or stats["parsed files"] < files_limit:
                if download_from_path:
                    download_filename = "../data/committees/download_document_committee_session/" + original_filename
                    if os.path.exists(download_filename):
                        with open(download_filename, "rb") as f:
                            with CommitteeMeetingProtocol.get_from_file(f) as protocol:
                                parse_protocol(output_filename, protocol)
                    else:
                        logging.warning("missing download_filename {}".format(download_filename))
                elif download_from_remote_storage:
                    url = download_from_remote_storage + original_filename
                    with CommitteeMeetingProtocol.get_from_url(url) as protocol:
                        parse_protocol(output_filename, protocol)
                else:
                    raise Exception("no valid download option")
            row.update(protocol_extension=ext,
                       parsed_filename=output_filename)
            yield row
        except Exception as e:
            # there is a bug in knesset-data-python which prevents getting the error message from the exception
            # TODO: fix this bug
            error_message = "failed to parse CommitteeSessionID {}".format(row["CommitteeSessionID"])  # , str(e))
            logging.exception(error_message)
            row.update(error=error_message)
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
datapackage["resources"][0]["schema"]["fields"] += [{"name": "protocol_extension", "type": "string"},
                                                    {"name": "parsed_filename", "type": "string"}]
datapackage["resources"][1].update(name="errors", path="errors.csv")
datapackage["resources"][1]["schema"]["fields"] += [{"name": "error", "type": "string"}]


spew(datapackage, get_resources(), stats)
