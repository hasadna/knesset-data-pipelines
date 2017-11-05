from datapackage_pipelines_knesset.common.base_processors.add_resource import AddResourceBaseProcessor
from sqlalchemy import or_
import os
import logging


class Processor(AddResourceBaseProcessor):

    def _get_schema(self, resource_descriptor):
        return resource_descriptor.get("schema", {
            "fields": [
                {"name": "url", "type": "string", "description": "url to download protocol from"},
                {"name": "kns_person_id", "type": "integer", "description": "primary key from kns_person table"}
            ],
            "primaryKey": ["kns_person_id"]
        })

    def _get_new_resource(self):
        person_table = self.db_meta.tables.get("kns_person")
        persontoposition_table = self.db_meta.tables.get("kns_persontoposition")
        if person_table is None or persontoposition_table is None:
            raise Exception("processor requires kns person tables to exist")
        override_meeting_ids = os.environ.get("OVERRIDE_PERSON_IDS")
        for db_row in self.db_session\
            .query(person_table, persontoposition_table)\
            .filter(persontoposition_table.c.PersonID==person_table.c.PersonID)\
            .filter(or_(*(documentcommitteesession_table.c.FilePath.like("%.{}".format(e)) for e in SUPPORTED_EXTENSIONS)))\
        .all():
            row = db_row._asdict()
            if str(row["GroupTypeID"]) == "23":
                if not override_meeting_ids or str(row["PersonID"]) in override_meeting_ids.split(","):
                    yield {"url": row["FilePath"],
                        "kns_person_id": row["PersonID"]}


if __name__ == "__main__":
    Processor.main()
