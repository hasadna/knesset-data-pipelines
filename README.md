# Knesset data pipelines

Knesset data scrapers and data sync

Uses the [datapackage pipelines framework](https://github.com/frictionlessdata/datapackage-pipelines) to scrape Knesset data


## Contributing

Looking to contribute? check out the [Help Wanted Issues](https://github.com/hasadna/knesset-data-pipelines/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22) or the [Noob Friendly Issues](https://github.com/hasadna/knesset-data-pipelines/issues?q=is%3Aissue+is%3Aopen+label%3A%22noob+friendly%22) for some ideas.


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




### Running the full pipelines environment using docker

#### A note for windows users:
Using windows with our docker environment is not currently recomended or supported. The build process seems to fail on numerous issues.
We suggest that windows users either dual-boot to Linux, or run Linux in virtualbox. Best supported version is Ubuntu 17.04
If you wish to use windows, do so at your own risk, and please update this README file with instructions if you succeed.

#### Instructions for running on Ubuntu (other distros and mac should follow a similar process):

* Install Docker
  * Ubuntu - [Docker Official Docs - Ubuntu installation](https://docs.docker.com/engine/installation/linux/docker-ce/ubuntu) - The recommended method is "Install using the repository")
  * Mac - https://store.docker.com/editions/community/docker-ce-desktop-mac
* Install docker-compose
  * Ubuntu - `sudo apt install docker-compose`
  * Mac - should be installed as part of the toolbox
* Make sure docker-compose is at version 1.13.0 or higher: `docker-compose --version`
  * If not, upgrade docker compose (refer to [Docker-compose Official Docs](https://docs.docker.com/compose/install/#install-compose))
* fork & clone the repo
* change directory to the repo's directory
* `sudo bin/start.sh`
* verify all dockers started correctly: `sudo docker ps` (should show 3 images running - app, db, redis)

This will provide:

* Pipelines dashboard: http://localhost:5000/
* PostgreSQL server, pre-populated with data: postgresql://postgres:123456@localhost:15432/postgres
* Minio object storage: http://localhost:9000/
  * Access Key = `admin`
  * Secret = `12345678`
* Adminer - DB Web UI: http://localhost:18080/
  * Database Type = PostgreSQL
  * Host = db
  * Port = 5432
  * Database = postgres
  * User = postgres
  * Password = 123456

After every change in the code you should run `sudo bin/build.sh && sudo bin/start.sh`


### Installing the project locally and running tests

You should have an activated python 3.6 virtualenv, following procedure will work on Ubuntu 17.04:
```
curl -kL https://raw.github.com/saghul/pythonz/master/pythonz-install | bash
echo '[[ -s $HOME/.pythonz/etc/bashrc ]] && source $HOME/.pythonz/etc/bashrc' >> ~/.bashrc
source ~/.bashrc
sudo apt-get install build-essential zlib1g-dev libbz2-dev libssl-dev libreadline-dev libncurses5-dev libsqlite3-dev libgdbm-dev libdb-dev libexpat-dev libpcap-dev liblzma-dev libpcre3-dev
pythonz install 3.6.2
sudo pip install virtualenvwrapper
echo 'export WORKON_HOME=$HOME/.virtualenvs; export PROJECT_HOME=$HOME/Devel; source /usr/local/bin/virtualenvwrapper.sh' >> ~/.bashrc
source ~/.bashrc
cd knesset-data-pipelines
mkvirtualenv -a `pwd` -p $HOME/.pythonz/pythons/CPython-3.6.2/bin/python3.6 knesset-data-pipelines
```

Before running any knesset-data-pipelines script, be sure to activate the virtualenv

You can do that by running `workon knesset-data-pipelines`

Once you are inside a Python 3.6 virtualenv, you can run the following:
* `bin/install.sh`
* `bin/test.sh`

You can set some environment variables to modify behaviors, see a refernece at .env.example

### Running the dpp cli

* using docker: `bin/dpp.sh`
* locally (from an activated virtualenv): `dpp`

### Run all pipelines at once

**Warning** this might seriously overload your CPU, use with caution..

```
docker-compose up -d redis db minio
source .env.example
for PIPELINE in `dpp | tail -n+2 | cut -d" " -f2 -`; do
    dpp run "${PIPELINE}" &
done
```

### Debugging committee meeting protocols

You should have the committee and session id of a meeting that you want to investigate

In this example the session id is `284231` and committee id is `196`

* Ensure an empty DB
  * `sudo rm -rf .data-docker/postgresql`
* Start the docker compose environment
  * `bin/start.sh`
* Wait ~20 seconds to ensure environment started properly
* Parse the protocols of the specific meeting / session id
  * `OVERRIDE_COMMITTEE_MEETING_IDS=284231 bin/dpp.sh run ./committees/committee-meeting-protocols`
* Check the parsed files in minio
  * minio default username=`admin`, password=`12345678`
  * original downloaded .doc: `284231.doc` - http://localhost:9000/minio/committees/protocols/original/196/
  * parsed files: `284231.txt` / `284231.csv` - http://localhost:9000/minio/committees/protocols/parsed/196/

### Updating the DB

The db image is updated with new data from time to time, to recreate the DB from scratch with latest data:

```
docker-compose stop db && sudo rm -rf .data-docker/postgresql/ && docker-compose up -d db
```


### Using boto with google cloud storage

* install gcloud SDK
* get a google service account secret key file
* `gcloud config set pass_credentials_to_gsutil false`
* `gsutil config -e`
