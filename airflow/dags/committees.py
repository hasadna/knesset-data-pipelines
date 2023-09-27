from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator

from knesset_data_pipelines.committees import background_material_titles


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
