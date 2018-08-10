from datapackage_pipelines.wrapper import process
from datapackage_pipelines.utilities.resources import PROP_STREAMING
import logging, os, csv, shutil
from knesset_data.protocols.committee import CommitteeMeetingProtocol
from datapackage_pipelines_knesset.common import utils
import crcmod, base64


def get_crc32c(filename):
    with open(filename, 'rb') as f:
        crc32c = crcmod.predefined.Crc('crc-32c')
        crc32c.update(f.read())
    return base64.b64encode(crc32c.digest()).decode()


def get_filenames(row, parameters):
    original_filename = os.path.join("files", str(row["GroupTypeID"]),
                                     str(row["DocumentCommitteeSessionID"])[0],
                                     str(row["DocumentCommitteeSessionID"])[1],
                                     str(row["DocumentCommitteeSessionID"]) + "." + row["ApplicationDesc"])
    ext = os.path.splitext(original_filename)[1].lower()
    output_filename = "files/{}/{}/{}.{}".format(str(row["CommitteeSessionID"])[0],
                                                 str(row["CommitteeSessionID"])[1],
                                                 str(row["CommitteeSessionID"]),
                                                 "csv" if parameters['type'] == "parts" else "txt")
    full_output_filename = parameters["out-path"] + "/" + output_filename
    download_filename = "../data/committees/download_document_committee_session/" + original_filename
    return original_filename, ext, output_filename, full_output_filename, download_filename


def process_row(row, row_index, resource_descriptor, resource_index, parameters, stats):
    if resource_descriptor['name'] == 'kns_documentcommitteesession':
        t = parameters['type']
        row[t + "_protocol_extension"] = None
        row[t + "_parsed_filename"] = None
        row[t + "_filesize"] = 0
        row[t + "_crc32c"] = None
        row[t + "_error"] = None
        if (row['GroupTypeID'] == 23 and row['ApplicationDesc'] == 'DOC'
            and (row["FilePath"].lower().endswith('.doc') or row["FilePath"].lower().endswith('.docx'))):
                document_id = "{}-{}-{}".format(row["GroupTypeID"], row["DocumentCommitteeSessionID"], row["ApplicationDesc"])
                original_filename, ext, output_filename, full_output_filename, download_filename = get_filenames(row, parameters)
                if os.path.exists(full_output_filename):
                    stats[t + ": existing files"] += 1
                    row[t + "_protocol_extension"] = ext
                    row[t + "_parsed_filename"] = output_filename
                    row[t + "_filesize"] = os.path.getsize(full_output_filename)
                    row[t + "_crc32c"] = get_crc32c(full_output_filename)
                elif os.path.exists(download_filename):
                    if parameters.get('files-limit') and parameters['files-limit'] <= stats[t + ": parsed files"]:
                        row[t + "_error"] = 'reached files-limit, skipping'
                        stats[t + ": skipped files"] += 1
                    else:
                        error_string = None
                        try:
                            with open(download_filename, "rb") as f:
                                with CommitteeMeetingProtocol.get_from_file(f) as protocol:
                                    os.makedirs(os.path.dirname(full_output_filename), exist_ok=True)
                                    with utils.temp_file() as temp_filename:
                                        with open(temp_filename, "w") as of:
                                            if parameters['type'] == "text":
                                                of.write(protocol.text)
                                            else:
                                                csv_writer = csv.writer(of)
                                                csv_writer.writerow(["header", "body"])
                                                for part in protocol.parts:
                                                    csv_writer.writerow([part.header, part.body])
                                        shutil.copy(temp_filename, full_output_filename)
                        except Exception as e:
                            logging.exception('exception parsing protocol for {}'.format(document_id))
                            try:
                                error_string = str(e)
                            except Exception:
                                error_string = 'unexpected exception'
                        if error_string:
                            row[t + "_error"] = error_string
                            stats[t + ': errored files'] += 1
                        else:
                            row[t + "_protocol_extension"] = ext
                            row[t + "_parsed_filename"] = output_filename
                            row[t + "_filesize"] = os.path.getsize(full_output_filename)
                            row[t + "_crc32c"] = get_crc32c(full_output_filename)
                            stats[t + ": parsed files"] += 1
                else:
                    row[t + "_error"] = 'missing download file'
                    stats[t + ': missing download files'] += 1
    return row


def modify_datapackage(datapackage, parameters, stats):
    t = parameters['type']
    stats[t + ': parsed files'] = 0
    stats[t + ': existing files'] = 0
    stats[t + ': skipped files'] = 0
    stats[t + ': errored files'] = 0
    stats[t + ': missing download files'] = 0
    fields = {t + "_protocol_extension": {'type': 'string'},
              t + "_parsed_filename": {'type': 'string'},
              t + "_filesize": {'type': 'integer'},
              t + "_crc32c": {'type': 'string'},
              t + "_error": {'type': 'string'},}
    for resource in datapackage['resources']:
        if resource['name'] == 'kns_documentcommitteesession':
            resource['schema']['fields'] = list(filter(lambda f: f['name'] not in fields, resource['schema']['fields']))
            resource['schema']['fields'] += [dict(f, name=fn) for fn, f in fields.items()]
    return datapackage


if __name__ == '__main__':
    process(modify_datapackage, process_row)
