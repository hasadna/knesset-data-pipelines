.PHONY: install install-optimized test docker-pull docker-build docker-start docker-clean docker-logs docker-stop

install:
	pip install -r requirements.txt
	which antiword > /dev/null || sudo apt-get install antiword
	pip install -e .[develop]

install-optimized:
	pip install -r requirements.txt
	pip install .

test:
	tox

docker-pull:
	docker pull orihoch/knesset-data-pipelines

docker-build:
	docker build -t orihoch/knesset-data-pipelines .

docker-start:
	mkdir -p .data-docker/postgresql
	docker-compose up -d

docker-clean:
	make docker-stop || true
	docker-compose rm -f

docker-logs:
	docker-compose logs

docker-stop:
	docker-compose stop

docker-deploy:
	docker-compose -f ./docker-compose.yml -f ./docker-compose-deployment.yml config > docker-compose-deployment-combined.yml
	docker stack deploy -c docker-compose-deployment-combined.yml
