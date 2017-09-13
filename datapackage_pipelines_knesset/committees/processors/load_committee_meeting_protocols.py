from datapackage_pipelines_knesset.common.base_processors.add_resource import AddResourceBaseProcessor
import logging
from sqlalchemy import inspect


class Processor(AddResourceBaseProcessor):

    def _get_schema(self, resource_descriptor):
        # can be extended to provide a hard-coded schema
        # or to modify the schema from the input resource descriptor
        return resource_descriptor.get("schema", {
            "fields": [
                {"name": "url", "type": "string"},
                {"name": "kns_committee_id", "type": "integer", "description": "primary key from kns_committee table"},
                {"name": "kns_session_id", "type": "integer",
                 "description": "primary key from kns_committeesession table"}
            ],
            "primaryKey": ["kns_session_id"]
        })

    def _get_new_resource(self):
        committee_table = self.db_meta.tables.get("kns_committee")
        committeesession_table = self.db_meta.tables.get("kns_committeesession")
        documentcommitteesession_table = self.db_meta.tables.get("kns_documentcommitteesession")
        if committee_table is None or committeesession_table is None or documentcommitteesession_table is None:
            raise Exception("processor requires kns committee tables to exist")
        for db_row in self.db_session\
            .query(committee_table, committeesession_table, documentcommitteesession_table)\
            .filter(committeesession_table.c.CommitteeID==committee_table.c.CommitteeID)\
            .filter(committeesession_table.c.CommitteeSessionID==documentcommitteesession_table.c.CommitteeSessionID)\
        .all():
            row = db_row._asdict()
            if str(row["GroupTypeID"]) == "23":
                yield {"url": row["FilePath"],
                       "kns_committee_id": row["CommitteeID"],
                       "kns_session_id": row["CommitteeSessionID"]}


if __name__ == "__main__":
    Processor.main()
