from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator

from knesset_data_pipelines.run_pipeline import list_pipelines, main as run_pipeline


dag_kwargs = dict(
    default_args={
        'owner': 'airflow',
    },
    schedule_interval='10 0 * * *',
    start_date=days_ago(1),
    catchup=False,
)

for pipeline_id in list_pipelines():
    with DAG(pipeline_id.replace('/', '.'), **dag_kwargs) as dag:
        PythonOperator(
            python_callable=run_pipeline,
            task_id=pipeline_id.replace('/', '.'),
            op_kwargs={'pipeline_id': pipeline_id}
        )
