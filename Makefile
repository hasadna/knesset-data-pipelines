.PHONY: install test clean docker-build docker-start docker-logs docker-logs-f docker-restart docker-clean-start docker-stop

install:
	pip install --upgrade pip setuptools
	pip install --upgrade -e .[develop]
	pip install --upgrade https://github.com/OriHoch/knesset-data-python/archive/gilwo-python-2-3.zip

test:
	tox -r

docker-build:
	docker build -t knesset-data-pipelines .

docker-start:
	docker-compose up -d

docker-logs:
	docker-compose logs

docker-logs-f:
	docker-compose logs -f

docker-restart:
	docker-compose restart
	make docker-logs-f

docker-clean-start:
	docker-compose down
	make docker-build
	make docker-start
	echo
	echo "waiting 5 seconds to let services start"
	sleep 5
	echo
	make docker-logs-f

docker-stop:
	docker-compose stop
