.PHONY: install test docker-pull docker-build docker-start docker-clean docker-logs docker-stop

install:
	pip install --upgrade https://github.com/hasadna/knesset-data-python/archive/v2.0.0.zip
	pip install -e .[develop]

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
