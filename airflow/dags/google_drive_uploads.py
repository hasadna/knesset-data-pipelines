from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator

from knesset_data_pipelines.google_drive_upload import committee_meeting_protocols


dag_kwargs = dict(
    default_args={
        'owner': 'airflow',
    },
    schedule_interval='10 0 * * *',
    start_date=days_ago(1),
    catchup=False,
)


with DAG('google_drive_uploads.committee_meeting_protocols', **dag_kwargs) as dag:
    PythonOperator(
        python_callable=committee_meeting_protocols.main,
        task_id='committee_meeting_protocols'
    )
