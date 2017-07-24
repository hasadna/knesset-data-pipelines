.PHONY: install test clean docker-build docker-restart docker-logs docker-stop

DB_PORT ?= 15432

install:
	pip install --upgrade https://github.com/hasadna/knesset-data-python/archive/v2.0.0.zip
	pip install -e .[develop]

test:
	tox

docker-build:
	docker build -t knesset-data-pipelines .

docker-restart:
	docker rm --force knesset-data-redis knesset-data-pipelines knesset-data-db || true
	docker network create knesset-data || true
	docker run --network knesset-data --name knesset-data-redis -d redis:alpine
	mkdir -p .data-docker/postgresql
	docker run --network knesset-data --name knesset-data-db -d -p $(DB_PORT):5432 -v `pwd`/.data-docker/postgresql:/var/lib/postgresql --env 'PG_PASSWORD=123456' sameersbn/postgresql:9.6-2
	docker run --network knesset-data --name knesset-data-pipelines --env DPP_REDIS_HOST=knesset-data-redis --env DPP_DB_ENGINE=postgresql://postgres:123456@knesset-data-db:5432/postgres -p 5000:5000 -d -v `pwd`/.data-docker:/knesset/data knesset-data-pipelines

docker-clean:
	docker rm --force knesset-data-redis knesset-data-pipelines knesset-data-db || true
	rm -rf .data-docker

docker-logs:
	docker logs knesset-data-redis
	docker logs knesset-data-db
	docker logs knesset-data-pipelines
