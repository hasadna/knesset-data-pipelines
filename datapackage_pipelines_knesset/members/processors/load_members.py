from datapackage_pipelines_knesset.common.base_processors.add_resource import AddResourceBaseProcessor

# only loads members with the following positionId:
SUPPORTED_POSITION_IDS = [43, 61]

class Processor(AddResourceBaseProcessor):

    def _get_schema(self, resource_descriptor):
        return resource_descriptor.get("schema", {
            "fields": [
                {"name": "url", "type": "string", "description": "url to download protocol from"},
                {
                    "name": "kns_person_id", "type": "integer",
                    "description": "primary key from kns_person table"}
            ],
            "primaryKey": ["kns_person_id"]
        })

    def _get_new_resource(self):
        person_table = self.db_meta.tables.get("kns_person")
        persontoposition_table = self.db_meta.tables.get("kns_persontoposition")
        if person_table is None or persontoposition_table is None:
            raise Exception("processor requires kns person tables to exist")
        for db_row in self.db_session\
            .query(person_table, persontoposition_table)\
            .filter(persontoposition_table.p.PersonID==person_table.p.PersonID)\
            .filter(persontoposition_table.p.PositionID.in_(SUPPORTED_POSITION_IDS))\
        .all():
            row = db_row._asdict()
            yield {"kns_person_id": row["PersonID"]}


if __name__ == "__main__":
    Processor.main()
