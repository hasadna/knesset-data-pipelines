import os


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
    'votes': "http://knesset.gov.il/KnessetOdataService/VotesData.svc",
    'messages': "http://knesset.gov.il/KnessetOdataService/KnessetMessagesData.svc",
    'mmm': "http://knesset.gov.il/KnessetOdataService/MMMData.svc",
    'lobbyists': "http://knesset.gov.il/Odata/Lobbyists.svc",
}
DEFAULT_REQUEST_TIMEOUT_SECONDS = 15

PGSQL_USER = os.environ.get('PGSQL_USER', 'postgres')
PGSQL_PASSWORD = os.environ.get('PGSQL_PASSWORD', '123456')
PGSQL_HOST = os.environ.get('PGSQL_HOST', 'localhost')
PGSQL_PORT = os.environ.get('PGSQL_PORT', '5432')
PGSQL_DB = os.environ.get('PGSQL_DB', 'postgres')
