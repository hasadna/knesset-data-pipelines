from datapackage_pipelines.wrapper import process
import logging, os, time
from datapackage_pipelines_knesset.retry_get_response_content import get_retry_response_content
import crcmod, base64


def get_crc32c(filename):
    with open(filename, 'rb') as f:
        crc32c = crcmod.predefined.Crc('crc-32c')
        crc32c.update(f.read())
    return base64.b64encode(crc32c.digest()).decode()


def process_row(row, row_index, resource_descriptor, resource_index, parameters, stats):
    if resource_descriptor['name'] == 'kns_documentcommitteesession':
        row.update(download_filename=None, download_filesize=0, download_crc32c=None, download_error=None)
        if (row['GroupTypeID'] == 23 and row['ApplicationDesc'] == 'DOC'
            and (row["FilePath"].lower().endswith('.doc') or row["FilePath"].lower().endswith('.docx'))):
                document_id = "{}-{}-{}".format(row["GroupTypeID"], row["DocumentCommitteeSessionID"], row["ApplicationDesc"])
                rel_filename = os.path.join("files", str(row["GroupTypeID"]),
                                            str(row["DocumentCommitteeSessionID"])[0],
                                            str(row["DocumentCommitteeSessionID"])[1],
                                            str(row["DocumentCommitteeSessionID"]) + "." + row["ApplicationDesc"])
                filename = os.path.join(parameters["out-path"], rel_filename)
                if os.path.exists(filename):
                    stats["download: existing files"] += 1
                    row.update(download_filename=rel_filename, download_filesize=os.path.getsize(filename),
                               download_crc32c=get_crc32c(filename))
                elif parameters.get('limit-rows') and stats["download: downloaded files"] >= parameters['limit-rows']:
                    row.update(download_error='reached limit, skipping download')
                    stats["download: skipped files"] += 1
                else:
                    error_string, content = None, ''
                    try:
                        content = get_retry_response_content(row["FilePath"], None, None, None, retry_num=1, num_retries=10,
                                                             seconds_between_retries=10,
                                                             skip_not_found_errors=True)
                    except Exception as e:
                        logging.exception('failed to download document id {}'.format(document_id))
                        try:
                            error_string = str(e)
                        except Exception:
                            error_string = 'unexpected exception'
                    time.sleep(0.01)
                    if error_string:
                        row.update(download_error=error_string)
                        stats['download: errored files'] += 1
                    else:
                        os.makedirs(os.path.dirname(filename), exist_ok=True)
                        with open(filename, "wb") as f:
                            f.write(content)
                        stats["download: downloaded files"] += 1
                        row.update(download_filename=rel_filename, download_filesize=os.path.getsize(filename),
                                   download_crc32c=get_crc32c(filename))
    return row


def modify_datapackage(datapackage, parameters, stats):
    stats["download: downloaded files"] = 0
    stats["download: existing files"] = 0
    stats["download: skipped files"] = 0
    stats["download: errored files"] = 0
    fields = {'download_filename': {'type': 'string'},
              'download_filesize': {'type': 'integer'},
              'download_crc32c': {'type': 'string'},
              'download_error': {'type': 'string'},}
    for resource in datapackage['resources']:
        if resource['name'] == 'kns_documentcommitteesession':
            resource['schema']['fields'] = list(filter(lambda f: f['name'] not in fields, resource['schema']['fields']))
            resource['schema']['fields'] += [dict(f, name=fn) for fn, f in fields.items()]
    return datapackage


if __name__ == '__main__':
    process(modify_datapackage, process_row)
