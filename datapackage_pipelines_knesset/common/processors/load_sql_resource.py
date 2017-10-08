from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
import json, logging
from datapackage_pipelines_knesset.common.db import get_session
from sqlalchemy import *
from datapackage_pipelines_knesset.common import object_storage

class LoadSqlResource(BaseProcessor):

    def __init__(self, parameters=None, datapackage=None, resources=None):
        super(LoadSqlResource, self).__init__(parameters, datapackage, resources)
        bucket = self._parameters["schema-bucket"]
        object_name = "table-schemas/{}.json".format(self._parameters["resource-name"])
        try:
            self._schema = json.loads(object_storage.read(bucket, object_name))
        except object_storage.NoSuchKey:
            raise Exception("missing schema {}".format(object_name))

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

    def _get_resource(self):
        meta = MetaData(bind=self.db_session.connection())
        meta.reflect()
        table = meta.tables.get(self._parameters["table"])
        if table is not None:
            for db_row in self.db_session.query(table).all():
                row = {}
                for field in self._schema["fields"]:
                    val = getattr(db_row, field["name"])
                    row[field["name"]] = val
                yield row
        self._process_cleanup()

    def _process(self, datapackage, resources):
        return self._process_append(datapackage, resources)


if __name__ == '__main__':
    LoadSqlResource.main()
