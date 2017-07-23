from collections import OrderedDict
from .mocks.dataservice import (MockDataserviceFunctionResourceProcessor,
                                MockAddDataserviceCollectionResourceProcessor)
from .common import get_pipeline_processor_parameters_schema, assert_conforms_to_schema
from itertools import chain


def get_committees():
    datapackage = {"name": "committees", "resources": []}
    processor_matcher = lambda step: step["run"] == "datapackage_pipelines_knesset.dataservice.processors.add_dataservice_collection_resource"
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
    processor_matcher = lambda step: step["run"] == "datapackage_pipelines_knesset.dataservice.processors.dataservice_function_resource"
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
