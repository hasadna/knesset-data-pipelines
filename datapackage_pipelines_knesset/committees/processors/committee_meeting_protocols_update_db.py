from datapackage_pipelines_knesset.common.processors.base_processor import BaseProcessor
import os, csv, logging
from datapackage_pipelines_knesset.common.db import get_session
from sqlalchemy import *

class CommitteeMeetingProtocolsUpdateDbProcessor(BaseProcessor):

    def __init__(self, *args, **kwargs):
        super(CommitteeMeetingProtocolsUpdateDbProcessor, self).__init__(*args, **kwargs)
        self._schema.update(fields=[{"name": "committee_id", "type": "integer"},
                                    {"name": "meeting_id", "type": "integer"},
                                    {"name": "header", "type": "string"},
                                    {"name": "body", "type": "string",
                                     "description": "relative path to the protocol file"},
                                    {"name": "order", "type": "integer"}],
                            primaryKey=["meeting_id", "order"])
        self._db_session = get_session()

    def _process(self, datapackage, resources):
        return self._process_filter(datapackage, resources)

    def _update_db(self, meeting_id, protocol_text):
        if not protocol_text:
            raise Exception("no protocol_text")
        logging.info("_update_db: {} {}".format(meeting_id, len(protocol_text)))
        meta = MetaData(bind=self._db_session.connection())
        try:
            meta.reflect()
            meetings = meta.tables[self._parameters["meetings-table"]]
            res = meetings.update().where(meetings.c.id==meeting_id).values(protocol_text=protocol_text).execute()
            # logging.info(res.last_updated_params())
            protocol_parts = meta.tables.get(self._parameters["protocol-parts-table"])
            if protocol_parts is not None:
                # delete all parts for this meeting (because they will be inserted in next pipeline)
                protocol_parts.delete().where(protocol_parts.c.meeting_id==meeting_id).execute()
        except Exception as e:
            logging.error("db error ({})".format(meta.bind.engine.url))
            raise
        self._db_session.commit()

    def _filter_row(self, meeting_protocol_parsed, **kwargs):
        committee_id, meeting_id = meeting_protocol_parsed["committee_id"], meeting_protocol_parsed["meeting_id"]
        with open(meeting_protocol_parsed["text_file"]) as f:
            self._update_db(meeting_id, f.read())
        with open(meeting_protocol_parsed["parts_file"]) as f:
            reader = csv.reader(f)
            next(reader)
            for order, row in enumerate(reader):
                yield {"committee_id": committee_id,
                       "meeting_id": meeting_id,
                       "header": row[0],
                       "body": row[1],
                       "order": order}


if __name__ == '__main__':
    CommitteeMeetingProtocolsUpdateDbProcessor.main()
