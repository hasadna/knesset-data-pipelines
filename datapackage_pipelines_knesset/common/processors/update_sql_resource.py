from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
import json, logging
from datapackage_pipelines_knesset.common.db import get_session
from sqlalchemy import *
from jsontableschema_sql import Storage
import jsontableschema
from jsontableschema_sql.storage import mappers


class UpdateSqlResource(BaseProcessor):

    def __init__(self, parameters=None, datapackage=None, resources=None):
        super(UpdateSqlResource, self).__init__(parameters, datapackage, resources)
        self.table_name = self._parameters["table"]
        self._schema = {"fields": [{"name": "id", "type": "integer"}]}
        self._table_schema = None
        for resource in self._datapackage["resources"]:
            if resource["name"] == self._parameters["output-resource"]:
                self._table_schema = resource["schema"]
        self.save_schema = self._parameters.get("save-schema")
        if self.save_schema:
            with open(self.save_schema, "w") as f:
                json.dump(self._table_schema, f)

    @property
    def db_session(self):
        if not hasattr(self, "_db_session"):
            self._db_session = self._get_new_db_session()
        return self._db_session

    def _get_new_db_session(self):
        return get_session()

    def _get_values(self, row):
        values = {}
        for k, v in row.items():
            if v == "":
                v = None
            values[k] = v
        return values

    def _upsert(self, id, values):
        if self._parameters.get("only-insert"):
            return self._insert(id, values)
        else:
            rows = self.db_session.query(self.db_table.c.id).filter(self.db_table.c.id == id).all()
            if len(rows) > 0:
                return self._update(id, values)
            else:
                return self._insert(id, values)

    def _update(self, id, values):
        for field_name, field_params in self._parameters.get("fields", {}).items():
            if field_params.get("dont-update"):
                values.pop(field_name)
        self.db_table.update().values(**values).where(self.db_table.c.id == id).execute()
        return {"id": id}

    def _insert(self, id, values):
        values["id"] = id
        self.db_table.insert().values(**values).execute()
        return {"id": id}

    def _filter_row(self, row, **kwargs):
        id = int(row.pop("id"))
        values = self._get_values(row)
        res = None
        if self.db_table is None:
            jsontableschema.validate(self._table_schema)
            prefix, bucket = "", self.table_name
            index_fields = []
            autoincrement = None
            tablename = mappers.bucket_to_tablename(prefix, bucket)
            columns, constraints, indexes = mappers.descriptor_to_columns_and_constraints(prefix, bucket,
                                                                                          self._table_schema,
                                                                                          index_fields,
                                                                                          autoincrement)
            self.db_table = Table(tablename, self.db_meta, *(columns + constraints + indexes))
            self.db_table.create()
        res = self._upsert(id, values)
        if res:
            yield res

    def _process_cleanup(self):
        self.db_session.commit()

    def _process(self, datapackage, resources):
        self.db_meta = MetaData(bind=self.db_session.connection())
        self.db_meta.reflect()
        self.db_table = self.db_meta.tables.get(self.table_name)
        return self._process_filter(datapackage, resources)


if __name__ == '__main__':
    UpdateSqlResource.main()
