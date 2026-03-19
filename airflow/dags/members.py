from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator

from knesset_data_pipelines.members_eng import members_eng
from knesset_data_pipelines.config import AIRFLOW_DEFAULT_EMAILS


dag_kwargs = dict(
    default_args={
        'owner': 'airflow',
    },
    schedule_interval='10 0 * * *',
    start_date=days_ago(1),
    catchup=False,
)


with DAG('members.members_eng', **dag_kwargs) as dag:
    PythonOperator(
        python_callable=members_eng.main,
        task_id='members_eng',
        email=AIRFLOW_DEFAULT_EMAILS,
    )
