from datapackage_pipelines_knesset.common.base_processors.add_resource import AddResourceBaseProcessor

# only loads documents which end with these extensions
SUPPORTED_APPLICATION_IDS = [1]
SUPPORTED_GROUP_TYPE_ID = 28


class Processor(AddResourceBaseProcessor):
    def _get_schema(self, resource_descriptor):
        return resource_descriptor.get("schema", {
            "fields": [
                {"name": "url", "type": "string", "description": "url to download protocol from"},
                {
                    "name": "kns_plenum_session_id", "type": "integer",
                    "description": "primary key from kns_plenumsession table"
                }
            ],
            "primaryKey": ["kns_plenum_session_id"]
        })

    def _get_new_resource(self):
        plenumsession_table = self.db_meta.tables.get("kns_plenumsession")
        document_table = self.db_meta.tables.get("kns_documentplenumsession")
        if plenumsession_table is None or document_table is None:
            raise Exception("processor requires kns plenum tables to exist")
        for db_row in self.db_session \
                .query(plenumsession_table, document_table) \
                .filter(plenumsession_table.c.PlenumSessionID == document_table.c.PlenumSessionID) \
                .filter(document_table.c.ApplicationID.in_(SUPPORTED_APPLICATION_IDS)) \
                .filter(document_table.c.GroupTypeID == SUPPORTED_GROUP_TYPE_ID) \
                .all():

            row = db_row._asdict()
            yield {"url": row["FilePath"],
                   "kns_plenum_session_id": row["PlenumSessionID"]}


if __name__ == "__main__":
    Processor.main()
