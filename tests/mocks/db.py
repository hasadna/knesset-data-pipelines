from datapackage_pipelines_knesset.common.db import get_connection
from sqlalchemy import *


def create_mock_db(session):
    conn = session.connection()
    metadata = MetaData(bind=conn)
    meetings = Table("committee-meetings", metadata,
                     Column("id", Integer),
                     Column("protocol_text", Text))
    meetings.create()
    protocol_parts = Table("committee-meeting-protocol-parts", metadata,
                           Column("committee_id", Integer),
                           Column("meeting_id", Integer),
                           Column("header", Text),
                           Column("body", Text),
                           Column("order", Integer))
    protocol_parts.create()
    meetings.insert().values(id=2020275, protocol_text="").execute()
    protocol_parts.insert().values(committee_id=1, meeting_id=2020275,
                                   header="header", body="body", order=0).execute()
    return metadata
