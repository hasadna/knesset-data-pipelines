from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
from datapackage_pipelines_knesset.common.db import get_session
from sqlalchemy import *
from datapackage_pipelines_knesset.common.utils import get_pipeline_schema
import logging

class LoadSqlResource(BaseProcessor):

    def __init__(self, parameters=None, datapackage=None, resources=None):
        super(LoadSqlResource, self).__init__(parameters, datapackage, resources)
        if not self._parameters.get("schema"):
            pipeline_spec = self._parameters["schema-bucket"]
            pipeline_id = self._parameters["resource-name"]
            self._schema = get_pipeline_schema(pipeline_spec, pipeline_id)
        else:
            self._schema = self._parameters["schema"]


    @property
    def db_session(self):
        if not hasattr(self, "_db_session"):
            self._db_session = self._get_new_db_session()
        return self._db_session

    def _get_new_db_session(self):
        return get_session()

    def _process_cleanup(self):
        self._db_session.commit()
        super(LoadSqlResource, self)._process_cleanup()

    def _filter_row(self, row, **kwargs):
        if "filter" in self._parameters:
            for field_name, filter_value in self._parameters["filter"].items():
                if not filter_value and row.get(field_name):
                    return False
                elif filter_value and not row.get(field_name):
                    return False
                elif row.get(field_name) != filter_value:
                    return False
        return True

    def _get_resource(self):
        meta = MetaData(bind=self.db_session.connection())
        meta.reflect()
        table = meta.tables.get(self._parameters["table"])
        if table is not None:
            for db_row in self.db_session.query(table):
                row = {}
                for field in self._schema["fields"]:
                    val = getattr(db_row, field["name"])
                    row[field["name"]] = val
                if self._filter_row(row):
                    yield row
        self._process_cleanup()

    def _process(self, datapackage, resources):
        return self._process_append(datapackage, resources)


if __name__ == '__main__':
    LoadSqlResource.main()
