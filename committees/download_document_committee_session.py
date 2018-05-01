from datapackage_pipelines.wrapper import ingest, spew
import logging, os, requests, time
from datapackage_pipelines_knesset.retry_get_response_content import get_retry_response_content
from copy import deepcopy
import crcmod, base64


stats = {"downloaded files": 0, "existing files": 0}


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
    filename = os.path.join(out_path, rel_filename)
    logging.info('downloading {}'.format(filename))
    if os.path.exists(filename):
        logging.info('file exists: {}'.format(filename))
        stats["existing files"] += 1
    else:
        content = get_retry_response_content(row["FilePath"], None, None, None, retry_num=1, num_retries=10,
                                             seconds_between_retries=10,
                                             skip_not_found_errors=skip_not_found_errors)
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as f:
            f.write(content)
        logging.info('downloaded file: {}'.format(filename))
        stats["downloaded files"] += 1
    return rel_filename, os.path.getsize(filename), get_crc32c(filename)


parameters, datapackage, resources = ingest()
out_path = parameters["out-path"]
errors = []
skip_not_found_errors = (os.environ.get("SKIP_NOT_FOUND_ERRORS") != "0")


def get_resource():
    for resource in resources:
        for row in resource:
            row.setdefault('filesize', 0)
            row.setdefault('crc32c', None)
            row.setdefault('error', None)
            document_id = "{}-{}-{}".format(row["GroupTypeID"], row["DocumentCommitteeSessionID"], row["ApplicationDesc"])
            try:
                filename, filesize, crc32c = download_document(row)
                row.update(filename=filename, filesize=filesize, crc32c=crc32c, error=None)
            except Exception as e:
                logging.exception('failed to download document id {}'.format(document_id))
                errors.append({'error': str(e)})
                row.update(filesize=None, crc32c=None, error=str(e))
            yield row
            time.sleep(0.01)


datapackage["resources"][0]["schema"]["fields"] += [{"name": "filename", "type": "string"},
                                                    {"name": "filesize", "type": "integer"},
                                                    {"name": "crc32c", "type": "string"},
                                                    {"name": "error", "type": "string"}]


spew(datapackage, [get_resource()], stats)
