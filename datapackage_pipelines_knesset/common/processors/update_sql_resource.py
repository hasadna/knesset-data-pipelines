from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
import json, logging
from datapackage_pipelines_knesset.common.db import get_session
from sqlalchemy import *
from tableschema_sql import Storage
import tableschema
from tableschema_sql.storage import mappers


class UpdateSqlResource(BaseProcessor):

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

    def _get_id_column(self):
        return getattr(self.db_table.c, self._id_field_name)

    def _upsert(self, id, values):
        logging.info("upsert: {}, {}".format(id, values))
        if self._parameters.get("only-insert"):
            return self._insert(id, values)
        else:
            rows = self.db_session.query(self._get_id_column()).filter(self._get_id_column() == id).all()
            logging.info(len(rows))
            if len(rows) > 0:
                return self._update(id, values)
            else:
                return self._insert(id, values)

    def _update(self, id, values):
        for field_name, field_params in self._parameters.get("fields", {}).items():
            if field_params.get("dont-update"):
                values.pop(field_name)
        self.db_table.update().values(**values).where(self._get_id_column() == id).execute()
        return {self._id_field_name: id}

    def _insert(self, id, values):
        logging.info("_insert: {}, {}".format(id, values))
        logging.info("id_field_name = {}".format(self._id_field_name))
        if id is not None:
            values[self._id_field_name] = id
        self.db_table.insert().values(**values).execute()
        return {self._id_field_name: id}

    def _filter_row(self, row, **kwargs):
        id = int(row.pop(self._id_field_name)) if self._id_field_name in row else None
        values = self._get_values(row)
        if self.db_table is None:
            tableschema.validate(self._table_schema)
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
            logging.info("Created DB table {}".format(tablename))
        res = self._upsert(id, values)
        if res:
            yield res

    def _process_cleanup(self):
        self.db_session.commit()

    def _process(self, datapackage, resources):
        self.table_name = self._parameters["table"]
        self._table_schema = None
        for resource in self._datapackage["resources"]:
            if resource["name"] == self._get_output_resource_name():
                self._schema = self._table_schema = resource["schema"]
        self._id_field_name = self._parameters.get("id-field-name", self._table_schema["primaryKey"][0])
        self.save_schema = self._parameters.get("save-schema", "../data/schemas/{}.json".format(self.table_name))
        if self.save_schema:
            with open(self.save_schema, "w") as f:
                json.dump(self._table_schema, f, indent=2, ensure_ascii=False)
        self.db_meta = MetaData(bind=self.db_session.connection())
        self.db_meta.reflect()
        self.db_table = self.db_meta.tables.get(self.table_name)
        return self._process_filter(datapackage, resources)


if __name__ == '__main__':
    UpdateSqlResource.main()
