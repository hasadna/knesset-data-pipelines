from datapackage_pipelines.wrapper import ingest, spew
import logging, os, requests, csv
from knesset_data.protocols.committee import CommitteeMeetingProtocol
from copy import deepcopy
from datapackage_pipelines_knesset.common import utils


parameters, datapackage, resources = ingest()
stats = {"parsed files": 0}
check_remote_storage = os.environ.get("CHECK_REMOTE_STORAGE", parameters.get("check-remote-storage"))
files_limit = int(os.environ.get("FILES_LIMIT", parameters.get("files-limit", "50")))
out_path = parameters["out-path"]
download_from_path = parameters.get("download-from-path")
download_from_remote_storage = parameters.get("download-from-remote-storage")
parse_type = parameters["type"]
errors = []


def file_exists(rel_filename):
    if check_remote_storage:
        url = check_remote_storage + rel_filename
        return requests.head(url).status_code == 200
    else:
        return None


def parse_protocol(output_filename, protocol):
    full_output_filename = out_path + "/" + output_filename
    os.makedirs(os.path.dirname(full_output_filename), exist_ok=True)
    if parse_type == "txt":
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
            os.rename(filename, full_output_filename)
            stats["parsed files"] += 1
    else:
        raise NotImplementedError


def get_resource(resource):
    for row in resource:
        try:
            original_filename = row["filename"]
            ext = os.path.splitext(original_filename)[1].lower()
            output_filename = "files/{}/{}/{}.{}".format(str(row["CommitteeSessionID"])[0],
                                                         str(row["CommitteeSessionID"])[1],
                                                         str(row["CommitteeSessionID"]),
                                                         "csv" if parse_type == "parts" else "txt")
            if stats["parsed files"] < files_limit and not file_exists(output_filename):
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
            logging.exception("failed to parse CommitteeSessionID {}".format(row["CommitteeSessionID"]))
            row.update(error=str(e))
            errors.append(row)
            if len(errors) > 1000:
                raise Exception("Too many errors!")


def get_errors_resource():
    for error in errors:
        yield error


def get_resources():
    for resource in resources:
        yield get_resource(resource)
    yield get_errors_resource()


datapackage["resources"].append(deepcopy(datapackage["resources"][0]))
datapackage["resources"][0]["schema"]["fields"] += [{"name": "protocol_extension", "type": "string"},
                                                    {"name": "parsed_filename", "type": "string"}]
datapackage["resources"][1].update(name="errors", path="errors.csv")
datapackage["resources"][1]["schema"]["fields"] += [{"name": "error", "type": "string"}]


spew(datapackage, get_resources(), stats)
