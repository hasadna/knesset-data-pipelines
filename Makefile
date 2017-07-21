.PHONY: install test clean docker-build docker-restart docker-logs docker-stop

install:
	pip install --upgrade https://github.com/OriHoch/knesset-data-python/archive/gilwo-python-2-3.zip
	pip install -e .[develop]

test:
	tox

docker-build:
	docker build -t knesset-data-pipelines .

docker-restart:
	docker rm --force knesset-data-redis knesset-data-pipelines || true
	docker network create knesset-data || true
	docker run --network knesset-data --name knesset-data-redis -d redis:alpine
	docker run --network knesset-data --name knesset-data-pipelines --env DPP_REDIS_HOST=knesset-data-redis -p 5000:5000 -d knesset-data-pipelines

docker-logs:
	docker logs knesset-data-redis
	docker logs knesset-data-pipelines
