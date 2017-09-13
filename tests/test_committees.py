from collections import OrderedDict
from .mocks.committees import (MockDownloadCommitteeMeetingProtocols, MockParseCommitteeMeetingProtocols)
from .common import assert_conforms_to_schema, get_pipeline_processor_parameters, assert_dataservice_processor_data
import os, datetime
from shutil import rmtree
import logging, json


def test_kns_committee():
    assert_dataservice_processor_data("committees", "kns_committee", [{
        'CommitteeID': 1,
        'Name': 'הכנסת',
        'CategoryID': 1,
        'CategoryDesc': 'ועדת הכנסת',
        'KnessetNum': 15,
        'CommitteeTypeID': 70,
        'CommitteeTypeDesc': 'ועדת הכנסת',
        'Email': 'vadatk@knesset.gov.il',
        'StartDate': datetime.datetime(1999, 6, 7, 0, 0),
        'FinishDate': None,
        'AdditionalTypeID': 991,
        'AdditionalTypeDesc': 'קבועה',
        'ParentCommitteeID': None,
        'CommitteeParentName': None, 'IsCurrent': True,
        'LastUpdatedDate': datetime.datetime(2017, 4, 24, 16, 47, 6)
    }])

def test_kns_committeesession():
    assert_dataservice_processor_data("committees", "kns_committeesession", [{
        'CommitteeSessionID': 64515, 'Number': None, 'KnessetNum': 16, 'TypeID': 161,
        'TypeDesc': 'פתוחה', 'CommitteeID': 22,
        'Location': 'חדר הוועדה, באגף הוועדות (קדמה), קומה 2, חדר 2750',
        'SessionUrl': 'http://main.knesset.gov.il/Activity/committees/Pages/AllCommitteesAgenda.aspx?Tab=3&ItemID=64515',
        'BroadcastUrl': None, 'StartDate': datetime.datetime(2003, 2, 25, 10, 30),
        'FinishDate': None, 'Note': None,
        'LastUpdatedDate': datetime.datetime(2012, 9, 19, 15, 27, 32)
    }, {
        'CommitteeSessionID': 64516, 'Number': 2, 'KnessetNum': 16, 'TypeID': 161,
        'TypeDesc': 'פתוחה', 'CommitteeID': 21,
        'Location': 'חדר הוועדה, באגף הוועדות (קדמה), קומה 3, חדר 3750',
        'SessionUrl': 'http://main.knesset.gov.il/Activity/committees/Pages/AllCommitteesAgenda.aspx?Tab=3&ItemID=64516',
        'BroadcastUrl': None, 'StartDate': datetime.datetime(2003, 2, 24, 10, 0),
        'FinishDate': None, 'Note': None,
        'LastUpdatedDate': datetime.datetime(2012, 9, 19, 15, 27, 32)
    }], expected_schema={
        'fields': [
            {'type': 'integer', 'description': 'מספר השורה בטבלה זו',
             'name': 'CommitteeSessionID'},
            {'type': 'integer', 'description': 'מספר הישיבה', 'name': 'Number'},
            {'type': 'integer', 'description': 'מספר הכנסת', 'name': 'KnessetNum'},
            {'type': 'integer', 'description': 'קוד סוג הישיבה', 'name': 'TypeID'},
            {'type': 'string', 'description': 'תיאור סוג הישיבה (פתוחה, חסויה, סיור)',
             'name': 'TypeDesc'},
            {'type': 'integer', 'description': 'קוד הוועדה', 'name': 'CommitteeID'},
            {'type': 'string', 'description': 'מיקום הישיבה', 'name': 'Location'},
            {'type': 'string', 'description': 'קישור לישיבה באתר הכנסת',
             'name': 'SessionUrl'},
            {'type': 'string', 'description': 'קישור לשידור הישיבה באתר הכנסת',
             'name': 'BroadcastUrl'},
            {'type': 'datetime', 'description': 'תאריך התחלה', 'name': 'StartDate',
             'format': 'fmt:%Y-%m-%d %H:%M:%S.%f'},
            {'type': 'datetime', 'description': 'תאריך סיום', 'name': 'FinishDate',
             'format': 'fmt:%Y-%m-%d %H:%M:%S.%f'},
            {'type': 'string', 'description': 'הערה', 'name': 'Note'},
            {'type': 'datetime', 'description': 'תאריך עדכון אחרון',
             'name': 'LastUpdatedDate', 'format': 'fmt:%Y-%m-%d %H:%M:%S.%f'}],
        'primaryKey': ['CommitteeSessionID']})



def test_download_committee_meeting_protocols():
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "test-committee-meeting-protocols")
    rmtree(out_path, ignore_errors=True)
    datapackage = {"name": "committee-meeting-protocols", "resources": [{"name": "kns_documentcommitteesession"}]}
    processor_matcher = lambda step: step["run"] == "..datapackage_pipelines_knesset.committees.processors.download_committee_meeting_protocols"
    parameters = get_pipeline_processor_parameters("committees", "committee-meeting-protocols", processor_matcher)
    parameters["out-path"] = out_path
    meeting_protocols = [{"kns_committee_id": 937, "kns_session_id": 2020275,
                          "url": "http://fs.knesset.gov.il//20/Committees/20_ptv_389210.doc"},
                         {"kns_committee_id": 191, "kns_session_id": 180774,
                          "url": "http://fs.knesset.gov.il//17/Committees/17_cs_bg_337938.rtf"},
                         {"kns_committee_id": 2, "kns_session_id": 2011909,
                          "url": "http://fs.knesset.gov.il//20/Committees/20_ptv_387483.doc"},
                         {"kns_committee_id": 926, "kns_session_id": 2019272,
                          "url": "http://fs.knesset.gov.il//20/Committees/20_cs_bg_388526.docx"}]
    processor = MockDownloadCommitteeMeetingProtocols(datapackage=datapackage, parameters=parameters, resources=[meeting_protocols])
    datapackage, resources = processor.spew()
    schema = datapackage["resources"][0]["schema"]
    resources = list(resources)
    assert len(resources) == 1
    resource = list(resources[0])
    assert len(resource) == 3
    protocol = resource[0]
    assert_conforms_to_schema(schema, protocol)
    assert protocol["protocol_file"] == os.path.join(out_path, "937", "2020275.doc")
    assert os.path.exists(protocol["protocol_file"])
    assert os.path.getsize(protocol["protocol_file"]) == 55296
    rtf_protocol = resource[1]
    assert_conforms_to_schema(schema, rtf_protocol)
    assert rtf_protocol["protocol_file"] == os.path.join(out_path, "191", "180774.rtf")
    assert os.path.exists(rtf_protocol["protocol_file"])
    assert os.path.getsize(rtf_protocol["protocol_file"]) == 86871
    with open(os.path.join(out_path, "datapackage.json")) as f:
        datapackage = json.load(f)
        assert datapackage == {"name": "_",
                               "resources": [{'name': 'committee-meeting-protocols',
                                              'path': ['937/2020275.doc', '191/180774.rtf', '926/2019272.docx']}]}

def test_parse_committee_meeting_protocols():
    # this is the input to the parse committee meeting protocols processor
    # it contains downloaded meeting protocol source files (either .doc or .rtf)
    downloaded_protocols = [{"kns_committee_id": 937, "kns_session_id": 2020275,
                             "url": "http://fs.knesset.gov.il//20/Committees/20_ptv_389210.doc",
                             "protocol_url": "test.example.com",
                             "protocol_file": os.path.join(os.path.dirname(__file__),
                                                                             "mocks", "20_ptv_389210.doc")},
                            # rtf file - will be skipped
                            {"kns_committee_id": 191, "kns_session_id": 180774,
                             "url": "http://fs.knesset.gov.il//17/Committees/17_cs_bg_337938.rtf",
                             "protocol_url": "test.example.com",
                             "protocol_file": os.path.join(os.path.dirname(__file__),
                                                           "mocks", "2007-12-27.rtf")},
                            # invalid file - will be skipped
                            {"kns_committee_id": 935, "kns_session_id": 576879,
                             "url": "http://fs.knesset.gov.il//20/Committees/20_ptv_341203.doc",
                             "protocol_url": "test.example.com",
                             "protocol_file": os.path.join(os.path.dirname(__file__),
                                                           "mocks", "20_ptv_341203.doc")},
                            # .docx - will be skipped
                            {"kns_committee_id": 926, "kns_session_id": 2019272,
                             "url": "http://fs.knesset.gov.il//20/Committees/20_cs_bg_388526.docx",
                             "protocol_url": "test.example.com",
                             "protocol_file": os.path.join(os.path.dirname(__file__),
                                                           "mocks", "20_cs_bg_388526.docx")}]
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
    resource = list(resources[0])
    # all docs are returned, but the invalid ones will have empty text / parts file
    assert len(resource) == 4

    parsed_url = lambda f: "https://next.oknesset.org/data/committee-meeting-protocols-parsed/{}".format(f)
    parsed_file = lambda f: os.path.join(out_path, f)

    expected_path = []

    # valid doc protocol
    valid_protocol = resource[0]
    assert_conforms_to_schema(schema, valid_protocol)
    assert valid_protocol["parts_url"] == parsed_url(os.path.join("937", "2020275.csv"))
    assert valid_protocol["text_url"] == parsed_url(os.path.join("937", "2020275.txt"))
    assert os.path.exists(parsed_file(os.path.join("937", "2020275.csv")))
    assert os.path.exists(parsed_file(os.path.join("937", "2020275.txt")))
    assert os.path.getsize(parsed_file(os.path.join("937", "2020275.csv"))) == 2335
    assert os.path.getsize(parsed_file(os.path.join("937", "2020275.txt"))) == 2306
    expected_path += ['937/2020275.csv', '937/2020275.txt']

    # valid rtf protocol
    rtf_protocol = resource[1]
    assert_conforms_to_schema(schema, rtf_protocol)
    if os.environ.get("RTF_EXTRACTOR_BIN"):
        assert rtf_protocol["parts_url"] == parsed_url(os.path.join("191", "180774.csv"))
        assert rtf_protocol["text_url"] == parsed_url(os.path.join("191", "180774.txt"))
        assert os.path.exists(parsed_file(os.path.join("191", "180774.csv")))
        assert os.path.exists(parsed_file(os.path.join("191", "180774.txt")))
        # TODO: change to the actual file sizes after parsing
        assert os.path.getsize(parsed_file(os.path.join("191", "180774.csv"))) == 2272
        assert os.path.getsize(parsed_file(os.path.join("191", "180774.txt"))) == 2246
        expected_path += ['191/180774.csv', '191/180774.txt']
    else:
        logging.warning("skipping rtf protocol test")
    
    # invalid doc - skipped
    invalid_doc = resource[2]
    assert_conforms_to_schema(schema, invalid_doc)
    assert invalid_doc["parts_url"] == None
    assert invalid_doc["text_url"] == None

    # .docx - skipped
    docx = resource[3]
    assert_conforms_to_schema(schema, docx)
    assert docx["parts_url"] == None
    assert docx["text_url"] == None

    # the datapackage contains only the valid files
    with open(os.path.join(out_path, "datapackage.json")) as f:
        datapackage = json.load(f)
        assert datapackage == {"name": "_",
                               "resources": [{'name': 'committee-meeting-protocols-parsed',
                                              'path': expected_path}]}
