from collections import OrderedDict
from .mocks.dataservice import (MockDataserviceFunctionResourceProcessor,
                                MockAddDataserviceCollectionResourceProcessor)
from .mocks.committees import (MockDownloadCommitteeMeetingProtocols, MockParseCommitteeMeetingProtocols)
from .common import (get_pipeline_processor_parameters_schema, assert_conforms_to_schema,
                     get_pipeline_processor_parameters)
from itertools import chain
import os, datetime
from shutil import rmtree
import logging, json
from datapackage_pipelines_knesset.committees.processors.parse_committee_meeting_attendees import ParseCommitteeMeetingAttendeesProcessor


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
    assert next(committees) == OrderedDict([('id', 1),
                                            ('type_id', 1),
                                            ('parent_id', None),
                                            ('name', 'ועדת הכנסת'),
                                            ('name_eng', 'House Committee'),
                                            ('name_arb', None),
                                            ('begin_date', datetime.datetime(1950, 1, 1, 0, 0)),
                                            ('end_date', None),
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
                                            ('description_arb', None),
                                            ('note', None),
                                            ('note_eng', None),
                                            ('portal_link', 'knesset')])
    assert next(committees)["id"] == 2


def test_committee_meetings():
    committee_meetings = get_committee_meetings()
    assert next(committee_meetings) == OrderedDict([('id', 2020374),
                                                        ('committee_id', 1),
                                                        ('datetime', datetime.datetime(2017, 7, 19, 11, 40)),
                                                        ('title',
                                                         'בקשת חהכ מרב מיכאלי להקדמת הדיון בהצעת חוק ההוצאה לפועל'
                                                         ' (תיקון – הפטר לחייב מוגבל באמצעים) התשעז-2017 (פ/4426/20)  '),
                                                        ('session_content',
                                                         'בקשת חה"כ מרב מיכאלי להקדמת הדיון בהצעת חוק ההוצאה לפועל'
                                                         ' (תיקון – הפטר לחייב מוגבל באמצעים) התשע"ז-2017 (פ/4426/20)  '),
                                                        ('url', None),
                                                        ('location', 'חדר ועדה'),
                                                        ('place', 'חדר הוועדה, באגף קדמה, קומה 3, חדר 3720'),
                                                        ('meeting_stop', '19/07/2017 11:40'),
                                                        ('agenda_canceled', 0),
                                                        ('agenda_sub', None),
                                                        ('agenda_associated', None),
                                                        ('agenda_associated_id', None),
                                                        ('agenda_special', None),
                                                        ('agenda_invited1', None),
                                                        ('agenda_invite', True),
                                                        ('note', None),
                                                        ('start_datetime', datetime.datetime(2017, 7, 19, 11, 40)),
                                                        ('topic_id', 13834),
                                                        ('creation_date', datetime.datetime(2017, 7, 19, 11, 40)),
                                                        ('streaming_url', 'http://video.knesset.gov.il/knesset'),
                                                        ('meeting_start', '19/07/2017 11:39'),
                                                        ('is_paused', False),
                                                        ('date_order', '2017-07-19'),
                                                        ('date', '19/07/2017'),
                                                        ('day', '19'),
                                                        ('month', 'יולי'),
                                                        ('material_id', None),
                                                        ('material_committee_id', None),
                                                        ('material_expiration_date', None),
                                                        ('material_hour', None),
                                                        ('old_url', None),
                                                        ('background_page_link', None),
                                                        ('agenda_invited', None)])
    assert next(committee_meetings)["id"] == 2020370

def test_committee_meeting_exception():
    committee_meetings = get_committee_meetings(committee_id="572")
    meeting = next(committee_meetings)
    assert meeting["id"] == 2019965

def test_download_committee_meeting_protocols():
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "test-committee-meeting-protocols")
    rmtree(out_path, ignore_errors=True)
    datapackage = {"name": "committee-meeting-protocols", "resources": [{"name": "committee-meetings"}]}
    processor_matcher = lambda step: step["run"] == "..datapackage_pipelines_knesset.committees.processors.download_committee_meeting_protocols"
    parameters = get_pipeline_processor_parameters("committees", "committee-meeting-protocols", processor_matcher)
    parameters["out-path"] = out_path
    meeting_protocols = [{"committee_id": 1, "id": 2020275,
                          "url": "http://fs.knesset.gov.il//20/Committees/20_ptv_389210.doc"},
                         {"committee_id": 1, "id": 268926,
                          "url": "http://knesset.gov.il/protocols/data/rtf/knesset/2007-12-27.rtf"},
                         {"committee_id": 2, "id": 2011909,
                          "url": "http://fs.knesset.gov.il//20/Committees/20_ptv_387483.doc"}]
    processor = MockDownloadCommitteeMeetingProtocols(datapackage=datapackage, parameters=parameters, resources=[meeting_protocols])
    datapackage, resources = processor.spew()
    schema = datapackage["resources"][0]["schema"]
    resources = list(resources)
    assert len(resources) == 1
    resource = list(resources[0])
    assert len(resource) == 2
    protocol = resource[0]
    assert_conforms_to_schema(schema, protocol)
    assert protocol["protocol_file"] == os.path.join(out_path, "1", "2020275.doc")
    assert os.path.exists(protocol["protocol_file"])
    assert os.path.getsize(protocol["protocol_file"]) == 55296
    rtf_protocol = resource[1]
    assert_conforms_to_schema(schema, rtf_protocol)
    assert rtf_protocol["protocol_file"] == os.path.join(out_path, "1", "268926.rtf")
    assert os.path.exists(rtf_protocol["protocol_file"])
    assert os.path.getsize(rtf_protocol["protocol_file"]) == 15370
    with open(os.path.join(out_path, "datapackage.json")) as f:
        datapackage = json.load(f)
        assert datapackage == {"name": "_",
                               "resources": [{'name': 'committee-meeting-protocols',
                                              'path': ['1/2020275.doc', '1/268926.rtf']}]}

def get_parsed_committee_meeting_protocols():
    # this is the input to the parse committee meeting protocols processor
    # it contains downloaded meeting protocol source files (either .doc or .rtf)
    downloaded_protocols = [{"committee_id": 1, "meeting_id": 2020275,
                             "url": "http://fs.knesset.gov.il//20/Committees/20_ptv_389210.doc",
                             "protocol_file": os.path.join(os.path.dirname(__file__),
                                                           "mocks", "20_ptv_389210.doc")},
                            # rtf file - will be skipped
                            {"committee_id": 1, "meeting_id": 268926,
                             "url": "http://knesset.gov.il/protocols/data/rtf/knesset/2007-12-27.rtf",
                             "protocol_file": os.path.join(os.path.dirname(__file__),
                                                           "mocks", "2007-12-27.rtf")},
                            # invalid file - will be skipped
                            {"committee_id": 5, "meeting_id": 576879,
                             "url": "http://fs.knesset.gov.il//20/Committees/20_ptv_341203.doc",
                             "protocol_file": os.path.join(os.path.dirname(__file__),
                                                           "mocks", "20_ptv_341203.doc")}]
    # output files will be saves in this path
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "test-parse-committee-meeting-protocols")
    rmtree(out_path, ignore_errors=True)
    datapackage = {"name": "committee-meeting-protocols-parse",
                   "resources": [{"name": "committee-meeting-protocols"}]}
    processor_matcher = lambda step: step["run"] == "..datapackage_pipelines_knesset" \
                                                    ".committees.processors.parse_committee_meeting_protocols"
    parameters = get_pipeline_processor_parameters("committees", "committee-meeting-protocols", processor_matcher)
    parameters["out-path"] = out_path
    processor = MockParseCommitteeMeetingProtocols(datapackage=datapackage, parameters=parameters,
                                                   resources=[downloaded_protocols])
    datapackage, resources = processor.spew()
    schema = datapackage["resources"][0]["schema"]
    resources = list(resources)
    assert len(resources) == 1
    return resources[0], schema, out_path


def test_parse_committee_meeting_protocols():
    resource, schema, out_path = get_parsed_committee_meeting_protocols()
    resource = list(resource)

    # all docs are returned, but the invalid ones will have empty text / parts file
    assert len(resource) == 3

    # valid doc protocol
    valid_protocol = resource[0]
    assert_conforms_to_schema(schema, valid_protocol)
    assert valid_protocol["parts_file"] == os.path.join(out_path, "1", "2020275.csv")
    assert valid_protocol["text_file"] == os.path.join(out_path, "1", "2020275.txt")
    assert os.path.exists(valid_protocol["parts_file"])
    assert os.path.exists(valid_protocol["text_file"])
    assert os.path.getsize(valid_protocol["parts_file"]) == 2335
    assert os.path.getsize(valid_protocol["text_file"]) == 2306

    # rtf and invalid doc - skipped
    for skipped_protocol in [resource[1], resource[2]]:
        assert_conforms_to_schema(schema, skipped_protocol)
        assert skipped_protocol["parts_file"] == None
        assert skipped_protocol["text_file"] == None

    # the datapackage contains only the valid files
    with open(os.path.join(out_path, "datapackage.json")) as f:
        datapackage = json.load(f)
        assert datapackage == {"name": "_",
                               "resources": [{'name': 'committee-meeting-protocols-parsed',
                                              'path': ['1/2020275.csv', '1/2020275.txt']}]}

def test_parse_committee_meeting_attendees():
    # get the input for the meeting attendees processor
    resource, schema, out_path = get_parsed_committee_meeting_protocols()
    parsed_meeting = next(resource)
    protocol_file = os.path.join(os.path.dirname(__file__), 'mocks', '20_ptv_389210.doc')
    text_file = os.path.join(out_path, '1', '2020275.txt')
    parts_file = os.path.join(out_path, '1', '2020275.csv')
    assert parsed_meeting == {'committee_id': 1, 'meeting_id': 2020275,
                              'protocol_file': protocol_file,
                              'text_file': text_file,
                              'parts_file': parts_file}
    # prepare the meeting attendees processor input
    datapackage = {"name": "_",
                   "resources": [{"name": "committee-meetings"}]}
    # we load the parameters by matching the processor step from the pipeline-spec.yaml file
    processor_matcher = lambda step: step["run"] == "..datapackage_pipelines_knesset" \
                                                    ".committees.processors.parse_committee_meeting_attendees"
    parameters = get_pipeline_processor_parameters("committees", "committee-meeting-attendees", processor_matcher)
    parameters["input-path"] = out_path
    processor = ParseCommitteeMeetingAttendeesProcessor(datapackage=datapackage, parameters=parameters,
                                                        resources=[[{"id": parsed_meeting["meeting_id"],
                                                                    "committee_id": parsed_meeting["committee_id"]}]])
    datapackage, resources = processor.spew()
    resources = list(resources)
    assert len(resources) == 1
    resource = list(resources[0])
    assert resource == [{'committee_id': 1, 'meeting_id': 2020275, 'name': 'דוד ביטן – היו"ר', 'role': 'mks', 'additional_information': ''},
                        {'committee_id': 1, 'meeting_id': 2020275, 'name': 'אמיר אוחנה', 'role': 'mks', 'additional_information': ''}, 
                        {'committee_id': 1, 'meeting_id': 2020275, 'name': 'דוד אמסלם', 'role': 'mks', 'additional_information': ''}, 
                        {'committee_id': 1, 'meeting_id': 2020275, 'name': 'יואב בן צור', 'role': 'mks', 'additional_information': ''}, 
                        {'committee_id': 1, 'meeting_id': 2020275, 'name': 'יואל חסון', 'role': 'mks', 'additional_information': ''}, 
                        {'committee_id': 1, 'meeting_id': 2020275, 'name': 'אברהם נגוסה', 'role': 'mks', 'additional_information': ''}, 
                        {'committee_id': 1, 'meeting_id': 2020275, 'name': 'ארבל אסטרחן', 'role': 'legal_advisors', 'additional_information': ''}, 
                        {'committee_id': 1, 'meeting_id': 2020275, 'name': 'אתי בן יוסף', 'role': 'manager', 'additional_information': ''}] 
