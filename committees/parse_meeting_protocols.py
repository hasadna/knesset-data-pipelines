from datapackage_pipelines.wrapper import ingest, spew
import logging, os, csv, shutil
from knesset_data.protocols.committee import CommitteeMeetingProtocol
from datapackage_pipelines_knesset.common import utils
import crcmod, base64


def get_crc32c(filename):
    with open(filename, 'rb') as f:
        crc32c = crcmod.predefined.Crc('crc-32c')
        crc32c.update(f.read())
    return base64.b64encode(crc32c.digest()).decode()


parameters, datapackage, resources = ingest()
stats = {"parsed files": 0, "existing files": 0}
out_path = parameters["out-path"]
parse_type = parameters["type"]


def get_filenames(row):
    original_filename = os.path.join("files", str(row["GroupTypeID"]),
                                     str(row["DocumentCommitteeSessionID"])[0],
                                     str(row["DocumentCommitteeSessionID"])[1],
                                     str(row["DocumentCommitteeSessionID"]) + "." + row["ApplicationDesc"])
    ext = os.path.splitext(original_filename)[1].lower()
    output_filename = "files/{}/{}/{}.{}".format(str(row["CommitteeSessionID"])[0],
                                                 str(row["CommitteeSessionID"])[1],
                                                 str(row["CommitteeSessionID"]),
                                                 "csv" if parse_type == "parts" else "txt")
    full_output_filename = out_path + "/" + output_filename
    download_filename = "../data/committees/download_document_committee_session/" + original_filename
    return original_filename, ext, output_filename, full_output_filename, download_filename


def parse_protocol(row):
    original_filename, ext, output_filename, full_output_filename, download_filename = get_filenames(row)
    if os.path.exists(full_output_filename):
        logging.info('file exists: {}'.format(full_output_filename))
        stats["existing files"] += 1
        filesize = os.path.getsize(full_output_filename)
        crc32c = get_crc32c(full_output_filename)
        logging.info('existing file: {}'.format(full_output_filename))
    elif os.path.exists(download_filename):
        with open(download_filename, "rb") as f:
            with CommitteeMeetingProtocol.get_from_file(f) as protocol:
                os.makedirs(os.path.dirname(full_output_filename), exist_ok=True)
                with utils.temp_file() as temp_filename:
                    with open(temp_filename, "w") as of:
                        if parse_type == "text":
                            of.write(protocol.text)
                        else:
                            csv_writer = csv.writer(of)
                            csv_writer.writerow(["header", "body"])
                            for part in protocol.parts:
                                csv_writer.writerow([part.header, part.body])
                    shutil.copy(temp_filename, full_output_filename)
        filesize = os.path.getsize(full_output_filename)
        crc32c = get_crc32c(full_output_filename)
        logging.info('parsed file: {}'.format(full_output_filename))
        stats["parsed files"] += 1
    else:
        logging.warning('missing document committee session file: {}'.format(download_filename))
        ext, output_filename, filesize, crc32c = None, None, 0, None
    return ext, output_filename, filesize, crc32c


def get_resource():
    for resource in resources:
        for row in resource:
            if not row["FilePath"].lower().endswith('.doc') and not row["FilePath"].lower().endswith('.docx'):
                continue
            row.setdefault('protocol_extension', None)
            row.setdefault('parsed_filename', None)
            row.setdefault('filesize', 0)
            row.setdefault('crc32c', None)
            row.setdefault('error', None)
            document_id = "{}-{}-{}".format(row["GroupTypeID"], row["DocumentCommitteeSessionID"], row["ApplicationDesc"])
            try:
                ext, filename, filesize, crc32c = parse_protocol(row)
                if ext and filename and filesize > 0 and crc32c:
                    row.update(protocol_extension=ext, parsed_filename=filename, filesize=filesize, crc32c=crc32c, error=None)
                else:
                    logging.error('failed to parse document id {}'.format(document_id))
                    row.update(protocol_extension=ext, parsed_filename=filename, filesize=filesize, crc32c=crc32c,
                               error='parse_protocol returned None')
            except Exception as e:
                logging.exception('exception parsing protocol for {}'.format(document_id))
                try:
                    error_string = str(e)
                except Exception:
                    error_string = 'exception'
                row.update(protocol_extension=None, parsed_filename=None, filesize=0, crc32c=None, error=error_string)
            yield row


datapackage["resources"][0]["schema"]["fields"] += [{"name": "protocol_extension", "type": "string"},
                                                    {"name": "parsed_filename", "type": "string"},
                                                    {"name": "filesize", "type": "integer"},
                                                    {"name": "crc32c", "type": "string"},
                                                    {"name": "error", "type": "string"},]


spew(datapackage, [get_resource()], stats)
