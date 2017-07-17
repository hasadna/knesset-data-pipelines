## Docker README

Docker is used to run all the services and apps in a consistent way for both development and production.

**For most changes you can just run the code directly / use the unit tests - no need to run the Docker**

### Installation (commands are for Ubuntu 17.04)

* [Install Docker](https://docs.docker.com/engine/installation/) (tested with version 17.03)
  * `sudo apt-get remove docker docker-engine docker-compose docker.io`
  * `sudo apt-get install apt-transport-https ca-certificates curl software-properties-common`
  * `curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -`
  * `sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu xenial stable"`
  * `sudo apt-get update`
  * `sudo apt-get install docker-ce`
* [Install Docker Compose](https://docs.docker.com/compose/install/)
  * ```curl -L https://github.com/docker/compose/releases/download/1.13.0/docker-compose-`uname -s`-`uname -m` | sudo tee /usr/local/bin/docker-compose > /dev/null```
  * `sudo chmod +x /usr/local/bin/docker-compose`
* fix Docker permissions
  * `sudo usermod -aG docker $USER`
  * `sudo su -l $USER`
  * `docker ps`
  * restart to make sure group change takes effect
* clean start
  * `make docker-clean-start`

### Modifying configurations

* `cp docker-compose.override.yml.example docker-compose.override.yml`
* modify docker-compose.override.yml
* you can override all settings in docker-compose.yml

### Modifying code and restarting the app

In the docker-compose.override - uncomment the volumes directive - this will mount the host directory inside docker

Now, every change in the code is reflected inside docker

Restart the app with `make docker-restart`

for a full rebuild and restart run: `make docker-clean-start`

### debugging

```
docker exec -it knessetdatapipelines_app_1 sh
dpp
```

You can also copy the data directory from inside docker - to get the sync log

```
docker cp knessetdatapipelines_app_1:/knesset/data knessetdatapipelines_data
```
