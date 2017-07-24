from datapackage_pipelines_knesset.common.db import get_connection
from sqlalchemy import *


def get_metadata():
    conn = get_connection(connection_string="sqlite://")
    meta = MetaData(bind=conn)
    # we create a minimal DB here just for testing, the real DB has more columns

    meetings = Table("committee-meetings", meta,
                     Column("meeting_id", Integer),
                     Column("protocol_text", Text))
    meetings.create()
    meetings.insert().values(meeting_id=2020275, protocol_text="").execute()

    protocol_parts = Table("committee-meeting-protocol-parts", meta,
                           Column("committee_id", Integer),
                           Column("meeting_id", Integer),
                           Column("header", Text),
                           Column("body", Text),
                           Column("order", Integer))
    protocol_parts.create()
    protocol_parts.insert().values(committee_id=1, meeting_id=2020275,
                                   header="header", body="body", order=0).execute()

    return meta
