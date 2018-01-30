from datapackage_pipelines.wrapper import ingest, spew
import zipfile, logging, os
from datapackage_pipelines_knesset.retry_get_response_content import get_retry_response_content
from datapackage_pipelines_knesset.common.utils import temp_file


parameters, datapackage, resources = ingest()
dry_run = parameters.get("dry-run")
out_file = parameters.get("out-file")
files_limit = os.environ.get("FILES_LIMIT")
if files_limit:
    files_limit = int(files_limit)
stats = {"num files": 0, "total size bytes": 0}


def get_resource():
    z = zipfile.ZipFile(out_file, "w")
    for resource in resources:
        for row in resource:
            parts_file_name = row["parts_file_name"]
            if not parts_file_name:
                continue
            if row["KnessetNum"] != 20:
                continue
            if row["StartDate"].year not in (2017, 2018):
                continue
            if files_limit and stats["num files"] >= files_limit:
                continue
            yield row
            stats["num files"] += 1
            stats["total size bytes"] += row["parts_file_size"] if row["parts_file_size"] else 0
            if not dry_run:
                content = get_retry_response_content("https://storage.googleapis.com/knesset-data-pipelines/{}".format(parts_file_name),
                                                     None, None, None, retry_num=1, num_retries=3, seconds_between_retries=2)
                with temp_file() as filename:
                    with open(filename, "wb") as f:
                        f.write(content)
                    z.write(filename, "{}.csv".format(row["CommitteeSessionID"]))
    z.close()


spew(datapackage, [get_resource()], stats)
