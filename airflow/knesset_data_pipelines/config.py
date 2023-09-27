import os
import tempfile
from contextlib import contextmanager


KNESSET_DATA_PIPELINES_AIRFLOW_ROOT_DIR = os.environ.get('KNESSET_DATA_PIPELINES_AIRFLOW_ROOT_DIR')
if not KNESSET_DATA_PIPELINES_AIRFLOW_ROOT_DIR:
    KNESSET_DATA_PIPELINES_AIRFLOW_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KNESSET_DATA_PIPELINES_ROOT_DIR = os.environ.get('KNESSET_DATA_PIPELINES_ROOT_DIR')
if not KNESSET_DATA_PIPELINES_ROOT_DIR:
    KNESSET_DATA_PIPELINES_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KNESSET_PIPELINES_DATA_PATH = os.environ.get('KNESSET_PIPELINES_DATA_PATH')
if not KNESSET_PIPELINES_DATA_PATH:
    KNESSET_PIPELINES_DATA_PATH = os.path.join(KNESSET_DATA_PIPELINES_ROOT_DIR, 'data')

KNESSET_LOAD_FROM_URL = os.environ.get('KNESSET_LOAD_FROM_URL') == 'yes'
DATASERVICE_LOAD_FROM_URL = os.environ.get('DATASERVICE_LOAD_FROM_URL') == 'yes'
KNESSET_DATASERVICE_INCREMENTAL = os.environ.get('KNESSET_DATASERVICE_INCREMENTAL') == 'yes'

KNESSET_DATA_OUTPUT_SUFFIX = os.environ.get('KNESSET_DATA_OUTPUT_PREFIX', '')

SERVICE_URLS = {
    # these are the new old apis
    'laws': "http://knesset.gov.il/Odata_old/LawsData.svc",
    'members': "http://knesset.gov.il/Odata_old/KnessetMembersData.svc",
    'committees': "http://knesset.gov.il/Odata_old/CommitteeScheduleData.svc",
    'api': 'http://knesset.gov.il/Odata/ParliamentInfo.svc/',
    # these services use the old urls
    'bills': "http://knesset.gov.il/KnessetOdataService/BillsData.svc",
    'final_laws': "http://knesset.gov.il/KnessetOdataService/FinalLawsData.svc",
    'votes': "https://knesset.gov.il/Odata/Votes.svc",
    'messages': "http://knesset.gov.il/KnessetOdataService/KnessetMessagesData.svc",
    'mmm': "http://knesset.gov.il/KnessetOdataService/MMMData.svc",
    'lobbyists': "http://knesset.gov.il/Odata/Lobbyists.svc",
}
DEFAULT_REQUEST_TIMEOUT_SECONDS = 360

PGSQL_USER = os.environ.get('PGSQL_USER', 'postgres')
PGSQL_PASSWORD = os.environ.get('PGSQL_PASSWORD', '123456')
PGSQL_HOST = os.environ.get('PGSQL_HOST', 'localhost')
PGSQL_PORT = os.environ.get('PGSQL_PORT', '5432')
PGSQL_DB = os.environ.get('PGSQL_DB', 'postgres')

GOOGLE_SERVICE_ACCOUNT_JSON = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
GOOGLE_COMMITTEE_MEETING_PROTOCOLS_DRIVE_ID = os.environ.get('GOOGLE_COMMITTEE_MEETING_PROTOCOLS_DRIVE_ID') or '0ABsWRQoKW8czUk9PVA'
GOOGLE_COMMITTEE_MEETING_PROTOCOLS_FOLDER_ID = os.environ.get('GOOGLE_COMMITTEE_MEETING_PROTOCOLS_FOLDER_ID') or '1Nd4HwN_qx2eYnTRdPSXSJ8t036-EGp-3'

DATASERVICE_HTTP_PROXY = os.environ.get('DATASERVICE_HTTP_PROXY')


@contextmanager
def get_google_service_account_json_file_name():
    with tempfile.NamedTemporaryFile('w', suffix='.json') as f:
        f.write(GOOGLE_SERVICE_ACCOUNT_JSON)
        f.flush()
        yield f.name
