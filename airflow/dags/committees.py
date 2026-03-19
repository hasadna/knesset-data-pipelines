from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator

from knesset_data_pipelines.committees import background_material_titles
from knesset_data_pipelines.committees import parsed_document_committee_sessions
from knesset_data_pipelines.config import AIRFLOW_DEFAULT_EMAILS


dag_kwargs = dict(
    default_args={
        'owner': 'airflow',
    },
    schedule_interval='10 0 * * *',
    start_date=days_ago(1),
    catchup=False,
)


with DAG('committees.background_material_titles', **dag_kwargs) as dag:
    PythonOperator(
        python_callable=background_material_titles.main,
        task_id='background_material_titles'
    )


with DAG('committees.parsed_document_committee_sessions', **dag_kwargs) as dag:
    PythonOperator(
        python_callable=parsed_document_committee_sessions.main,
        task_id='parsed_document_committee_sessions'
    )
