from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
import logging

class DumpFields(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super(DumpFields, self).__init__(*args, **kwargs)

        self._schema = self._parameters.get("schema")
        self._dump_fields = self._parameters.get("dump-fields")
        self._constants = self._parameters.get("constants", {})

    def _process(self, datapackage, resources):
        return self._process_filter(datapackage, resources)

    def _filter_row(self, row, **kwargs):
        fields = self._constants
        for field, name in self._dump_fields.items():
            fields[name] = row[field]

        yield fields

if __name__ == "__main__":
    DumpFields.main()