from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from datapackage_pipelines_knesset.common import db
import logging


class ParseCommitteeMeetingAttendeesAliases(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super(ParseCommitteeMeetingAttendeesAliases, self).__init__(*args, **kwargs)
        self._schema["fields"] = [{"name": "alias_name", "type": "string"},
                                  {"name": "alias_type", "type": "string"}]
        self._schema["primaryKey"] = ["alias_name"]

    def _process(self, datapackage, resources):
        return self._process_filter(datapackage, resources)

    def _filter_row(self, row, **kwargs):
        name = self._parameters.get("name", "name")
        type = self._parameters.get("type", "meeting")

        yield {"alias_name": row[name].strip(), "alias_type": type}

if __name__ == "__main__":
    ParseCommitteeMeetingAttendeesAliases.main()
