from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
import os, csv, json


class ExtractFiles(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super(ExtractFiles, self).__init__(*args, **kwargs)
        for resource in self._datapackage["resources"]:
            if resource["name"] == self._parameters["input-resource"]:
                self._schema = resource["schema"]

    def _get_filename(self, relative_path):
        return os.path.join(self._parameters["out-path"], relative_path)

    def _filter_row(self, row, **kwargs):
        for file in self._parameters["files"]:
            relpath = file["relative-path"].format(**row)
            if relpath not in self._all_filenames:
                self._all_filenames.append(relpath)
                first_row = True
            else:
                first_row = False
            filename = self._get_filename(relpath)
            if first_row:
                mode = "w"
                os.makedirs(os.path.dirname(filename), exist_ok=True)
            else:
                mode = "a"
            if file.get("field"):
                content = row[file["field"]]
                row[file["field"]] = ""
                if content:
                    with open(filename, mode) as f:
                        f.write(content)
            elif file.get("fields"):
                with open(filename, mode) as f:
                    writer = csv.writer(f)
                    if first_row:
                        writer.writerow(file["fields"])
                    csv_row = []
                    for field in file["fields"]:
                        csv_row.append(row[field])
                        row[field] = ""
                    writer.writerow(csv_row)
            else:
                raise NotImplementedError()
        yield row

    def _process_cleanup(self):
        with open(self._get_filename("datapackage.json"), "w") as f:
            descriptor = {"name": "_", "path": self._all_filenames}
            descriptor.update(**self._parameters.get("data-resource-descriptor", {}))
            json.dump({"name": "_", "resources": [descriptor]}, f)

    def _process(self, datapackage, resources):
        self._all_filenames = []
        return self._process_filter(datapackage, resources)


if __name__ == '__main__':
    ExtractFiles.main()
