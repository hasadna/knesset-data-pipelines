import datetime
from functools import partial

import requests
from ruamel import yaml
from airflow import DAG
from airflow.utils.dates import days_ago
from airflow.operators.python import PythonOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import models as k8s
from airflow.models import DagRun
from airflow import settings
from sqlalchemy.orm import sessionmaker

from knesset_data_pipelines.run_pipeline import list_pipelines, main as run_pipeline


dag_kwargs = dict(
    default_args={
        'owner': 'airflow',
    },
    schedule_interval='10 0 * * *',
    start_date=days_ago(1),
    catchup=False,
)


PIPELINES_DOCKER_IMAGE = yaml.safe_load(requests.get('https://raw.githubusercontent.com/OriHoch/knesset-data-k8s/master/apps/pipelines/values-hasadna-auto-updated.yaml').text)['image']


def get_execution_dates(execution_date, external_dag_id, **kwargs):
    Session = sessionmaker()
    session = Session(bind=settings.engine)
    delta = datetime.timedelta(hours=6)
    earliest_time = execution_date - delta
    try:
        latest_run = session.query(DagRun).filter(
            DagRun.dag_id == external_dag_id,
            DagRun.execution_date >= earliest_time,
            DagRun.state == 'success'
        ).order_by(DagRun.execution_date.desc()).first()
        if latest_run:
            return [latest_run.execution_date]
        else:
            return []
    finally:
        session.close()


for params_error, pipeline_id, pipeline_dependencies, pipeline_schedule in list_pipelines(all_=True, with_dependencies=True):
    pipeline_dag_id = pipeline_id.replace('/', '.')
    with DAG(pipeline_dag_id, **{**dag_kwargs, 'schedule_interval': ('10 0 * * *' if pipeline_schedule else None)}) as dag:
        if params_error:
            main_task = KubernetesPodOperator(
                namespace='oknesset',
                name=f"airflow-{pipeline_dag_id}",
                image=PIPELINES_DOCKER_IMAGE,
                cmds=['/usr/local/bin/dpp'],
                arguments=['run', '--verbose', '--no-use-cache', f'./{pipeline_id}'],
                volumes=[
                    k8s.V1Volume(name='k8s-ops', secret=k8s.V1SecretVolumeSource(secret_name='ops')),
                    k8s.V1Volume(name='data', nfs=k8s.V1NFSVolumeSource(server='172.16.0.9', path='/mnt/sdb3/srv/default/oknesset/pipelines/data/oknesset-nfs-gcepd')),
                ],
                volume_mounts=[
                    k8s.V1VolumeMount(name='k8s-ops', mount_path='/secret_service_key', sub_path='secret.json', read_only=True),
                    k8s.V1VolumeMount(name='data', mount_path='/pipelines/data', sub_path='data'),
                    k8s.V1VolumeMount(name='data', mount_path='/pipelines/dist', sub_path='dist'),
                ],
                env_vars=[
                    k8s.V1EnvVar(name='DPP_DB_ENGINE', value_from=k8s.V1EnvVarSource(secret_key_ref=k8s.V1SecretKeySelector(name='publicdb', key='DPP_DB_ENGINE'))),
                    k8s.V1EnvVar(name='DUMP_TO_STORAGE', value='1'),
                    k8s.V1EnvVar(name='DUMP_TO_SQL', value='1'),
                    k8s.V1EnvVar(name='GOOGLE_APPLICATION_CREDENTIALS', value='/secret_service_key'),
                    k8s.V1EnvVar(name='DISABLE_MEMBER_PERCENTS', value='yes'),
                    k8s.V1EnvVar(name='TIKA_SERVER_ENDPOINT', value='http://tika:9998'),
                    k8s.V1EnvVar(name='PYTHONUNBUFFERED', value='1'),
                ],
                container_resources=k8s.V1ResourceRequirements(
                    requests={'cpu': '0.5', 'memory': '1.5Gi'},
                    limits={'cpu': '1.5', 'memory': '2Gi'},
                ),
                node_selector={
                    'oknesset-allowed-ip': 'true'
                },
                random_name_suffix=True,
                task_id=pipeline_dag_id,
                dag=dag
            )
        else:
            main_task = PythonOperator(
                python_callable=run_pipeline,
                task_id=pipeline_id.replace('/', '.'),
                op_kwargs={'pipeline_id': pipeline_id},
                dag=dag
            )
        for dependency in pipeline_dependencies:
            dependency_dag_id = dependency.replace('/', '.')
            ExternalTaskSensor(
                task_id=f'wait_{dependency_dag_id}',
                external_dag_id=dependency_dag_id,
                execution_date_fn=partial(get_execution_dates, external_dag_id=dependency_dag_id),
                mode='reschedule',
                dag=dag
            ) >> main_task
