# Knesset Data Pipelines Airflow

This is the Airflow implementation of the Knesset Data Pipelines project. It is a work in progress, during which we 
will be migrating the existing pipelines to Airflow.

The Airflow project is defined under `airflow` subdirectory, all the following commands are assumed to run from there.

## Local Development

Prerequisites:

* System dependencies: https://airflow.apache.org/docs/apache-airflow/stable/installation.html#system-dependencies
* Python 3.8

Create virtualenv and install dependencies

```
python3.8 -m venv venv &&\
. venv/bin/activate &&\
pip install --upgrade pip setuptools wheel &&\
bin/pip_install_airflow.sh &&\
pip install -e .
```

Authenticate with gcloud:

```
gcloud auth application-default login
```

Start a Database:

```
docker-compose up -d db
```

Run commands from the CLI:

```
knesset-data-pipelines --help
```

Optionally, to use Airflow locally:

Create a `.env` file with the following contents:

```
export AIRFLOW_HOME=$(pwd)/.airflow
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/dags
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__CORE__LOAD_DEFAULT_CONNECTIONS=False
export AIRFLOW__CORE__DAG_DISCOVERY_SAFE_MODE=False
export SQLALCHEMY_SILENCE_UBER_WARNING=1
```

Initialize the Airflow DB and create an admin user:

```
. venv/bin/activate &&\
. .env &&\
airflow db init &&\
airflow users create --username admin --firstname Admin --lastname Adminski \
    --role Admin --password 12345678 --email admin@localhost
```

Start the Airflow web server:

```
. venv/bin/activate && . .env && airflow webserver --port 8080
```

In a new terminal, start the Airflow scheduler:

```
. venv/bin/activate && . .env && airflow scheduler
```

Access the airflow webserver at [http://localhost:8080](http://localhost:8080) login using admin / 12345678

## Using docker-compose

```
docker-compose up -d --build
```