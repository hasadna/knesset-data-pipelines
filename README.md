# Knesset data pipelines

Knesset data scrapers and data sync

Uses the [datapackage pipelines framework](https://github.com/frictionlessdata/datapackage-pipelines) to scrape Knesset data and produce JSON+CSV files for useful queries.

This flow is executed periodically and resulting files are copied to Google Cloud Storage for use by the static web site generator and (in the future) oknesset APIs.


## Contributing

Looking to contribute? check out the [Help Wanted Issues](https://github.com/hasadna/knesset-data-pipelines/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) or the [Noob Friendly Issues](https://github.com/hasadna/knesset-data-pipelines/issues?q=is%3Aissue+is%3Aopen+label%3A%22noob+friendly%22) for some ideas.

Useful resources for getting acquainted:
* [DPP](https://github.com/frictionlessdata/datapackage-pipelines) documentation
* [Code](https://github.com/OriHoch/knesset-data-k8s) for the periodic execution component
* Pipelines developed in other repos: [People](https://github.com/OriHoch/knesset-data-people), [Committees](https://github.com/OriHoch/knesset-data-committees)
* [Info](http://main.knesset.gov.il/Activity/Info/Pages/Databases.aspx) on available data from the Knesset site
* Living [document](https://docs.google.com/document/d/1eeQRrpGYuEJKAAtShPbjFn6i2f_UmQgg1caMTEs93ic/edit) with short list of ongoing project activities


## Running the pipelines locally

Most pipelines are available to run locally with minimal infrastructure dependencies.

Install some dependencies (following works for latest version of Ubuntu):

```
sudo apt-get install -y python3.6 python3-pip python3.6-dev libleveldb-dev libleveldb1v5
sudo pip3 install pipenv
```

install the pipeline dependencies

```
pipenv install
```

activate the virtualenv

```
pipenv shell
```

Install the python module

```
pip install -e .
```

List the available pipelines

```
dpp
```

run a pipeline

```
dpp run <PIPELINE_ID>
```


## downloading the dataservices knesset data

The Knesset API is sometimes blocked / throttled from certain IPs.

To overcome this we provide the core data available for download so pipelines that process the data don't need to call the Knesset API directly.

You can set the `DATASERVICE_LOAD_FROM_URL=1` to enable download for pipelines that support it:

```
DATASERVICE_LOAD_FROM_URL=1 pipenv run dpp run ./committees/kns_committee
```


## dumping data to redash DB

This is used to populate the obudget redash at http://data.obudget.org/

To test locally, start a postgresql server:

```
docker run -d --rm --name postgresql -p 5432:5432 -e POSTGRES_PASSWORD=123456 postgres
```

Run the all package with dump.to_sql enabled

```
DPP_DB_ENGINE=postgresql://postgres:123456@localhost:5432/postgres pipenv run dpp run ./committees/all
```

Run the dump to db pipeline:

```
DPP_DB_ENGINE=postgresql://postgres:123456@localhost:5432/postgres dpp run ./knesset/dump_to_db
```

Start adminer to browse the data

```
docker run -d --name adminer -p 8080:8080 --link postgresql adminer
```

* Adminer is available at http://localhost:8080
  * system: postgresql, server: postgresql, username: postgres, password: 123456, database: postgres

Remove the containers when done

```
docker rm --force adminer postgresql
```

## running using docker

```
docker pull orihoch/knesset-data-pipelines
docker run -it --entrypoint bash -v `pwd`:/pipelines orihoch/knesset-data-pipelines
```

Continue with `Running the pipelines locally` section above

You can usually fix permissions problems on the files by running inside the docker `chown -R 1000:1000 .`

If you have access to the required secrets and google cloud account, you can use the following command to run with all required dependencies:

```
docker build -t knesset-data-pipelines . &&\
docker run -it --entrypoint bash \
           -e DUMP_TO_STORAGE=1 -e DUMP_TO_SQL=1 \
           -e RUN_PIPELINE_CMD="dpp run" \
           -e DPP_DB_ENGINE=postgresql://postgres:123456@postgresql:5432/postgres \
           -v `pwd`/secret-k8s-ops.json:/secret_service_key \
           --link postgresql \
           knesset-data-pipelines /pipelines/pipelines_script.sh
```


## testing docker build locally using google cloud

this is similar to what the continuous deployment does

Replace UNIQUE_TAG_NAME with a unique id for the image, e.g. the name of the branch you are testing

```
IMAGE_TAG="gcr.io/hasadna-oknesset/knesset-data-pipelines:UNIQUE_TAG_NAME"
CLOUDSDK_CORE_PROJECT=hasadna-oknesset
PROJECT_NAME=knesset-data-pipelines
gcloud  --project ${CLOUDSDK_CORE_PROJECT} container builds submit \
        --substitutions _IMAGE_TAG=${IMAGE_TAG},_CLOUDSDK_CORE_PROJECT=${CLOUDSDK_CORE_PROJECT},_PROJECT_NAME=${PROJECT_NAME} \
        --config continuous_deployment_cloudbuild.yaml .
```