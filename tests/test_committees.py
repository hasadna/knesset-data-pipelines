from collections import OrderedDict
from .mocks.dataservice import (MockDataserviceFunctionResourceProcessor,
                                MockAddDataserviceCollectionResourceProcessor)
from .mocks.committees import (MockDownloadCommitteeMeetingProtocols, MockParseCommitteeMeetingProtocols,
                               MockCommitteeMeetingProtocolsUpdateDb)
from .mocks.db import create_mock_db
from .common import (get_pipeline_processor_parameters_schema, assert_conforms_to_schema,
                     get_pipeline_processor_parameters)
from itertools import chain
import os, pytest
from shutil import rmtree
from datapackage_pipelines_knesset.common.db import get_session


def get_committees():
    datapackage = {"name": "committees", "resources": []}
    processor_matcher = lambda step: step["run"] == "..datapackage_pipelines_knesset.dataservice.processors.add_dataservice_collection_resource"
    parameters, schema = get_pipeline_processor_parameters_schema("committees", "committees",
                                                                  processor_matcher)
    processor = MockAddDataserviceCollectionResourceProcessor(datapackage=datapackage,
                                                              parameters=parameters)
    datapackage, resources = processor.spew()
    assert datapackage == {'name': 'committees',
                           'resources': [{'name': 'committees',
                                          'path': 'committees.csv',
                                          'schema': schema}]}
    resources = list(resources)
    assert len(resources) == 1
    resource = resources[0]
    first_row = next(resource)
    assert_conforms_to_schema(schema, first_row)
    return chain([first_row], resource)


def get_committee_meetings(committee_id=None):
    if not committee_id:
        committees = get_committees()
    else:
        committees = (o for o in [{"id": committee_id}])
    datapackage = {"name": "committee-meetings", "resources": [{"name": "committees"}]}
    processor_matcher = lambda step: step["run"] == "..datapackage_pipelines_knesset.dataservice.processors.dataservice_function_resource"
    parameters, schema = get_pipeline_processor_parameters_schema("committees", "committee-meetings",
                                                                  processor_matcher)
    parameters["parameters"]["FromDate"].update(source="date", date="2017-07-23")
    parameters["parameters"]["ToDate"].update(source="date", date="2017-07-23")
    processor = MockDataserviceFunctionResourceProcessor(datapackage=datapackage, parameters=parameters,
                                                         resources=[[next(committees)]])
    datapackage, resources = processor.spew()
    assert datapackage == {'name': 'committee-meetings',
                           'resources': [{'name': 'committee-meetings',
                                          'path': 'committee-meetings.csv',
                                          'schema': schema}]}
    resources = list(resources)
    assert len(resources) == 1
    resource = resources[0]
    first_row = next(resource)
    assert_conforms_to_schema(schema, first_row)
    return chain([first_row], resource)


def test_committees():
    committees = get_committees()
    assert next(committees) == OrderedDict([('id', "1"),
                                            ('type_id', "1"),
                                            ('parent_id', ""),
                                            ('name', 'ועדת הכנסת'),
                                            ('name_eng', 'House Committee'),
                                            ('name_arb', ""),
                                            ('begin_date', "1950-01-01"),
                                            ('end_date', ""),
                                            ('description',
                                             'תקנון הכנסת ועניינים הנובעים ממנו; חסינות חברי הכנסת ובקשות '
                                             'לנטילתה; סדרי הבית; המלצות על הרכב הוועדות הקבועות והוועדות '
                                             'לעניינים מסוימים, ויושבי-הראש שלהן; תיחום ותיאום עבודות '
                                             'הוועדות; העברת בקשות המוגשות לכנסת מן הציבור ליושב-ראש הכנסת או '
                                             'לוועדות המתאימות; דיון בתלונות על חברי הכנסת; תשלומים לחברי '
                                             'הכנסת; דיון בבקשות ובעניינים שאינם נוגעים לשום ועדה או שלא '
                                             'נכללו בתפקידי ועדה אחרת.'),
                                            ('description_eng',
                                             'The Committee deals with the following issues: the Knesset '
                                             'Rules of Procedure and all matters stemming from it; the '
                                             'immunity of Knesset members and requests for lifting it; the '
                                             'rules of the House; recommendations regarding the Parliamentary '
                                             'Groups and personal make-up of the permanent committees and the '
                                             'committes on a particular matter, as well as the appointment of '
                                             'their chairmen; the distribution of functions amongst the '
                                             'committees and coordination between them; decisions regarding '
                                             'the transfer of bills to the appropriate committee; the passing '
                                             'on of requests presented to the Knesset by the public for the '
                                             'Knesset Speaker or one of the Knesset committees; payments to '
                                             'Knesset members; discussions on requests and matters that are '
                                             'not connected to any committee or are not included among the '
                                             'functions of another committee. \r\n'),
                                            ('description_arb', ""),
                                            ('note', ""),
                                            ('note_eng', ""),
                                            ('portal_link', 'knesset')])
    assert next(committees)["id"] == "2"


def test_committee_meetings():
    committee_meetings = get_committee_meetings()
    assert next(committee_meetings) == OrderedDict([('id', "2020374"),
                                                    ('committee_id', "1"),
                                                    ('datetime', "2017-07-19 11:40:00.000000"),
                                                    ('title',
                                                     'בקשת חהכ מרב מיכאלי להקדמת הדיון בהצעת חוק ההוצאה לפועל'
                                                     ' (תיקון – הפטר לחייב מוגבל באמצעים) התשעז-2017 (פ/4426/20)  '),
                                                    ('session_content',
                                                     'בקשת חה"כ מרב מיכאלי להקדמת הדיון בהצעת חוק ההוצאה לפועל'
                                                     ' (תיקון – הפטר לחייב מוגבל באמצעים) התשע"ז-2017 (פ/4426/20)  '),
                                                    ('url', ""),
                                                    ('location', 'חדר ועדה'),
                                                    ('place', 'חדר הוועדה, באגף קדמה, קומה 3, חדר 3720'),
                                                    ('meeting_stop', '19/07/2017 11:40'),
                                                    ('agenda_canceled', "0"),
                                                    ('agenda_sub', ""),
                                                    ('agenda_associated', ""),
                                                    ('agenda_associated_id', ""),
                                                    ('agenda_special', ""),
                                                    ('agenda_invited1', ""),
                                                    ('agenda_invite', "true"),
                                                    ('note', ""),
                                                    ('start_datetime', "2017-07-19 11:40:00.000000"),
                                                    ('topic_id', "13834"),
                                                    ('creation_date', "2017-07-19 11:40:00.000000"),
                                                    ('streaming_url', 'http://video.knesset.gov.il/knesset'),
                                                    ('meeting_start', '19/07/2017 11:39'),
                                                    ('is_paused', "false"),
                                                    ('date_order', '2017-07-19'),
                                                    ('date', '19/07/2017'),
                                                    ('day', '19'),
                                                    ('month', 'יולי'),
                                                    ('material_id', ""),
                                                    ('material_committee_id', ""),
                                                    ('material_expiration_date', ""),
                                                    ('material_hour', ""),
                                                    ('old_url', ""),
                                                    ('background_page_link', ""),
                                                    ('agenda_invited', "")])
    assert next(committee_meetings)["id"] == "2020370"

def test_committee_meeting_exception():
    committee_meetings = get_committee_meetings(committee_id="572")
    meeting = next(committee_meetings)
    assert meeting["id"] == "2019965"

def test_download_committee_meeting_protocols():
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "test-committee-meeting-protocols")
    rmtree(out_path, ignore_errors=True)
    datapackage = {"name": "committee-meeting-protocols", "resources": [{"name": "committee-meetings"}]}
    processor_matcher = lambda step: step["run"] == "..datapackage_pipelines_knesset.committees.processors.download_committee_meeting_protocols"
    parameters = get_pipeline_processor_parameters("committees", "committee-meeting-protocols", processor_matcher)
    parameters["out-path"] = out_path
    meeting_protocols = [{"committee_id": 1, "id": 2020275,
                          "url": "http://fs.knesset.gov.il//20/Committees/20_ptv_389210.doc"}]
    processor = MockDownloadCommitteeMeetingProtocols(datapackage=datapackage, parameters=parameters, resources=[meeting_protocols])
    datapackage, resources = processor.spew()
    schema = datapackage["resources"][0]["schema"]
    resource = next(resources)
    protocol = next(resource)
    assert_conforms_to_schema(schema, protocol)
    assert protocol["protocol_file"] == os.path.join(out_path, "1", "2020275.doc")
    assert os.path.exists(protocol["protocol_file"])
    assert os.path.getsize(protocol["protocol_file"]) == 55296

@pytest.mark.skip
def test_parse_committee_meeting_protocols():
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "test-parse-committee-meeting-protocols")
    rmtree(out_path, ignore_errors=True)
    datapackage = {"name": "committee-meeting-protocols-parse", "resources": [{"name": "committee-meeting-protocols"}]}
    processor_matcher = lambda step: step["run"] == "..datapackage_pipelines_knesset.committees.processors.parse_committee_meeting_protocols"
    parameters = get_pipeline_processor_parameters("committees", "committee-meeting-protocols-parse", processor_matcher)
    parameters["out-path"] = out_path
    processor = MockParseCommitteeMeetingProtocols(datapackage=datapackage, parameters=parameters,
                                                   resources=[[{"committee_id": 1, "meeting_id": 2020275,
                                                                "url": "http://fs.knesset.gov.il//20/Committees/20_ptv_389210.doc",
                                                                "protocol_file": os.path.join(os.path.dirname(__file__), "mocks", "20_ptv_389210.doc")}]])
    datapackage, resources = processor.spew()
    schema = datapackage["resources"][0]["schema"]
    resource = next(resources)
    protocol = next(resource)
    assert_conforms_to_schema(schema, protocol)
    assert protocol["parts_file"] == os.path.join(out_path, "1", "2020275.parts.csv")
    assert protocol["text_file"] == os.path.join(out_path, "1", "2020275.txt")
    assert os.path.exists(protocol["parts_file"])
    assert os.path.exists(protocol["text_file"])
    assert os.path.getsize(protocol["parts_file"]) == 2335
    assert os.path.getsize(protocol["text_file"]) == 2306

@pytest.mark.skip
def test_committee_meeting_protocols_update_db():
    session = get_session(connection_string="sqlite://")
    metadata = create_mock_db(session)
    meetings = metadata.tables["committee-meetings"]
    protocol_parts = metadata.tables["committee-meeting-protocol-parts"]
    # the meeting is initially synced with empty protocol_text
    # the update_db processor will update it
    row = meetings.select(meetings.c.id == 2020275).execute().fetchone()
    assert row[meetings.c.protocol_text] == ""
    # the update_db processor also deletes any existing protocol parts
    # so we ensure we have one to see that it's deleted
    rows = protocol_parts.select(protocol_parts.c.meeting_id == 2020275).execute().fetchall()
    assert len(rows) == 1
    # setup the processor
    datapackage = {"name": "committee-meeting-protocols-update-db",
                   "resources": [{"name": "committee-meeting-protocols-parsed"}]}
    processor_matcher = lambda step: step["run"] == "..datapackage_pipelines_knesset.committees.processors.committee_meeting_protocols_update_db"
    parameters = get_pipeline_processor_parameters("committees", "committee-meeting-protocols-parse",
                                                   processor_matcher)
    meeting_protocols_parsed = [{"committee_id": 1, "meeting_id": 2020275,
                                 "url": "http://fs.knesset.gov.il//20/Committees/20_ptv_389210.doc",
                                 "protocol_file": os.path.join(os.path.dirname(__file__), "mocks", "20_ptv_389210.doc"),
                                 "parts_file": os.path.join(os.path.dirname(__file__), "mocks", "2020275.parts.csv"),
                                 "text_file": os.path.join(os.path.dirname(__file__), "mocks", "2020275.txt")}]
    processor = MockCommitteeMeetingProtocolsUpdateDb(datapackage=datapackage, parameters=parameters,
                                                      resources=[meeting_protocols_parsed])
    processor._db_session = session
    # set the db metadata on the mock processor, instead of
    datapackage, resources = processor.spew()
    schema = datapackage["resources"][0]["schema"]
    resource = next(resources)
    protocol_part = next(resource)
    assert_conforms_to_schema(schema, protocol_part)
    assert protocol_part == {'body': 'הכנסת העשרים\n\nמושב שלישי\n\nפרוטוקול מס\' 277\n\nמישיבת ועדת הכנסת\n\nיום שלישי, כ"ד בתמוז התשע"ז (18 ביולי 2017), שעה 11:00',
                             'committee_id': 1,
                             'header': '',
                             'meeting_id': 2020275,
                             'order': 0}
    assert next(resource) == {'body': 'בקשת חה"כ דוד ביטן להקדמת הדיון בהצעת חוק בנימין זאב הרצל (הנצחת זכרו ופועלו) (תיקון – מימון פעילות מוסדות ההנצחה), התשע"ז-2017 (פ/4414/20) לפני הקריאה הטרומית.',
                              'committee_id': 1,
                              'header': 'סדר היום',
                              'meeting_id': 2020275,
                              'order': 1}
    row = meetings.select(meetings.c.id==2020275).execute().fetchone()
    assert row
    assert row[meetings.c.id] == 2020275
    assert len(row[meetings.c.protocol_text]) == 1342
    # ensure all protocol parts were deleted
    rows = protocol_parts.select(protocol_parts.c.meeting_id == 2020275).execute().fetchall()
    assert len(rows) == 0
