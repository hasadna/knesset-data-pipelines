from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator

from knesset_data_pipelines import kns_odata
from knesset_data_pipelines.config import AIRFLOW_DEFAULT_EMAILS


dag_kwargs = dict(
    default_args={
        'owner': 'airflow',
    },
    schedule_interval='10 0 * * *',
    start_date=days_ago(1),
    catchup=False,
)


with DAG('kns_odata', **dag_kwargs) as dag:
    PythonOperator(
        python_callable=kns_odata.compare_parliamentinfo_tables_pipelines,
        task_id='compare_parliamentinfo_tables_pipelines',
        email=AIRFLOW_DEFAULT_EMAILS,
    )
