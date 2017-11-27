from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
import logging

class DumpFields(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super(DumpFields, self).__init__(*args, **kwargs)

        self._schema = self._parameters.get("schema")

    def _process(self, datapackage, resources):
        return self._process_filter(datapackage, resources)

    def _filter_row(self, row, **kwargs):
        fields = {}

        for field in self._schema["fields"]:
            value = row[field["from"]] if "from" in field else field["const"]

            if not value:
                value = field["default"]

            fields[field["name"]] = value

        yield fields

if __name__ == "__main__":
    DumpFields.main()