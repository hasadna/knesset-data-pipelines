# Knesset data pipelines

Data processing pipelines for loading, processing and visualizing data about the Knesset

We are in the process of migrating to airflow, see [airflow/README.md](airflow/README.md) for details.

Uses the [datapackage pipelines](https://github.com/frictionlessdata/datapackage-pipelines) and [DataFlows](https://github.com/datahq/dataflows) frameworks.

## Quickstart for data science

Follow this method to get started quickly with exploration, processing and testing of the knesset data.

### Running using Docker

Docker is required to run the notebooks to provide a consistent environment.

Install Docker for [Windows](https://store.docker.com/editions/community/docker-ce-desktop-windows),
[Mac](https://store.docker.com/editions/community/docker-ce-desktop-mac) or [Linux](https://docs.docker.com/install/)

Pull the latest Docker image

```
docker pull orihoch/knesset-data-pipelines
```

#### Run Jupyter Lab

Create a directory which will be shared between the host PC and the container:

```
sudo mkdir -p /opt/knesset-data-pipelines
```

Start the Jupyter lab server:

```
docker run -it -p 8888:8888 --entrypoint jupyter \
           -v /opt/knesset-data-pipelines:/pipelines \
           orihoch/knesset-data-pipelines lab --allow-root --ip 0.0.0.0 --no-browser \
                --NotebookApp.token= --NotebookApp.custom_display_url=http://localhost:8888/
```

Access the server at http://localhost:8888/

Open a terminal inside the Jupyter Lab web-ui, and clone the knesset-data-pipelines project:

```
git clone https://github.com/hasadna/knesset-data-pipelines.git .
```

You should now see the project files on the left sidebar.

Access the `jupyter-notebooks` directory and open one of the available notebooks.

You can now add or make modifications to the notebooks, then open a pull request with your changes.

You can also modify the pipelines code from the host machine and it will be reflected in the notebook environment.

#### Running from Local copy of knesset-data-pipelines

From your local PC, clone the repository into ./knesset-data-pipelines:

```
git clone https://github.com/hasadna/knesset-data-pipelines.git .
```

Change directory:

```
cd knesset-data-pipelines
```

Run with Docker, mounting the local directory

```
docker run -it -p 8888:8888 --entrypoint jupyter \
           -v `pwd`:/pipelines \
           orihoch/knesset-data-pipelines lab --allow-root --ip 0.0.0.0 --no-browser \
                --NotebookApp.token= --NotebookApp.custom_display_url=http://localhost:8888/
```

When running using this setup, you might have permission problems, fix it giving yourself ownership:

```
sudo chown -R $USER . 
```

### Running locally without Docker

Following instructions were tested with Ubuntu 18.04

Install system dependencies:

```
sudo apt-get install python3.6 python3.6-dev build-essential libxml2-dev libxslt1-dev libleveldb1v5 libleveldb-dev \
                     python3-pip bash jq git openssl antiword python3-venv
```

Install Python dependencies:

```
python3.6 -m venv env
source env/bin/activate
pip install 'https://github.com/OriHoch/datapackage-pipelines/archive/1.7.1-oh-2.zip#egg=datapackage-pipelines[speedup]'
pip install wheel
pip install psycopg2-binary knesset-data requests[socks] botocore boto3 python-dotenv google-cloud-storage sh
pip install datapackage-pipelines-metrics psutil crcmod jsonpickle tika kvfile pyquery dataflows==0.0.14 pymongo \
            tabulate jupyter jupyterlab
pip install -e .
```

Start environment (these steps are required each time before starting to run pipelines):

```
source env/bin/activate
export KNESSET_PIPELINES_DATA_PATH=`pwd`/data
```

Now you can run pipelines with `dpp` or start the notebook server with `jupyter lab`

## Contributing

Looking to contribute? check out the [Help Wanted Issues](https://github.com/hasadna/knesset-data-pipelines/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) or the [Noob Friendly Issues](https://github.com/hasadna/knesset-data-pipelines/issues?q=is%3Aissue+is%3Aopen+label%3A%22noob+friendly%22) for some ideas.

Useful resources for getting acquainted:
* [DPP](https://github.com/frictionlessdata/datapackage-pipelines) documentation
* [Code](https://github.com/OriHoch/knesset-data-k8s) for the periodic execution component
* [Info](http://main.knesset.gov.il/Activity/Info/Pages/Databases.aspx) on available data from the Knesset site
* Living [document](https://docs.google.com/document/d/1eeQRrpGYuEJKAAtShPbjFn6i2f_UmQgg1caMTEs93ic/edit) with short list of ongoing project activities

