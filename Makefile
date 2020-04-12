TAG ?=dev
PROJECT =mybnbaid
ROOT =${CURDIR}
export

# service variables
SERVICE_NAME ?=xyz
SERVICES ?=mail sms users zones properties bookings cleans gateway
LOCAL_LIBS ?=schemaless backless

# AWS secrets manager variables
GET_SECRET =aws secretsmanager get-secret-value --secret-id
PARSE_FIELD =jq -r
PARSE_SECRET =jq -r ".SecretString"
SECRET_KEY :=
SECRET_FIELD :=

# DB secret and connection variables
DB :=
SCHEMA :=
TABLE :=


include Make.in

.PHONY: secrets logs libs

build: build-images

push: push-images

persistence:
	$(call _info, starting persistence layers)
	docker-compose -f datastore-compose.yml rm -f schemaless memstore redstore
	docker-compose -f datastore-compose.yml stop schemaless memstore redstore
	docker-compose -f datastore-compose.yml up -d --remove-orphans schemaless memstore redstore

install: deps
	$(call _info, installing project services)
	for service in $(SERVICES); \
	do make -C $$service install-service; \
	done

deps:
	$(call _info, installing project dependencies)
	for lib in $(LOCAL_LIBS); \
	do make -C dependencies/$$lib install; \
	done

libs:
	$(call _info, installing project dependencies)
	for lib in $(LOCAL_LIBS); \
	do pip install git+ssh://git@github.com/peekwez/$$lib.git; \
	done

supervisor:
	$(call _info, creating supervisor configuration for services)
	backless process -c config.yml

start: install logs supervisor
	$(call _info, starting service processes)
	sleep 5
	supervisord -c supervisord.conf

stop:
	$(call _info, stopping service processes)
	supervisorctl stop all
	supervisorctl shutdown

status:
	$(call _info, checking status of service processes)
	supervisorctl status

prune:
	$(call _info, prunning dangling docker assets)
	docker system prune

network:
	$(call _info, creating a docker bridge network)
	docker network create \
	--driver=bridge \
	--subnet=192.168.0.0/24 \
	--gateway=192.168.0.1 \
	$(PROJECT)

compose:
	$(call _info, starting docker-compose services)
	docker-compose up -d --remove-orphans $(SERVICES)

logs:
	$(call _info, creating log files)
	rm -fr logs && mkdir logs
	touch logs/supervisor.log \
		logs/broker.logs logs/access.log \
		logs/error.log
	for service in $(SERVICES); \
	do touch logs/$$service.log; done

init-db:
	$(call _info, initializing service databases)
	backless syncdb -c datastore.yml

check-table: secrets
	$(call _info, checking table $(SCHEMA).$(TABLE) for $(DB) database)
	psql $(SECRET) -c "SELECT * FROM $(SCHEMA).$(TABLE);"

check-config: secrets
	$(call _info, check schemaless config for $(DB) database)
	psql $(SECRET) -c "SELECT * FROM public.tables;" 
	psql $(SECRET) -c "SELECT * FROM public.indexes;" 

close-cons: secrets 
	$(call _info, closing connections to $(DB) database)
	psql $(SECRET) -c "SELECT pg_terminate_backend(pid) \
	FROM pg_stat_activity WHERE datname='$(DB)'"

drop-db:
	$(call _info, dropping $(DB) database)
	psql $(SECRET) -c "DROP DATABASE IF EXISTS $(DB);"

create-db: close-cons drop-db
	$(call _info, creating $(DB) database)
	psql $(SECRET) -c "CREATE DATABASE $(DB);"

secrets:
	$(call _info, fetching secret from aws secrets manager)
	$(eval SECRET = $(shell $(GET_SECRET) $(SECRET_KEY) | $(PARSE_SECRET) | $(PARSE_FIELD) ".$(SECRET_FIELD)"))

upload-secrets:
	$(call _info, uploading secrets folder to aws s3)
	aws s3 cp secrets/development s3://mybnbaid/secrets/development --recursive
	aws s3 cp secrets/production s3://mybnbaid/secrets/production --recursive

create-service:
	$(call _info, initializing a service template)
	backless template -d $(ROOT) -s $(SERVICE_NAME)
	chmod a+x $(ROOT)/$(SERVICE_NAME)/run.sh
	git add $(SERVICE_NAME)/*

build-base:
	$(call _info, building base docker image)
	docker build -t $(PROJECT).base \
	-f docker/docker.base .

build-wheel-builder: build-base
	$(call _info, building dependencies in base docker image)
	docker build -t $(PROJECT).builder \
	-f docker/docker.build .

run-wheel-builder: build-wheel-builder
	$(call _info, installing depdencies in base docker image)
	for image in $(IMAGES); \
	do make -C $$image run-wheel-builder; \
	done

build-images: run-wheel-builder
	$(call _info, building docker images for services)
	for image in $(IMAGES); \
	do make -C $$image build-image; \
	done

docker-login:
	$(call _info, logging into docker account)
	docker login --username=$(DOCKER_USERNAME) \
	--password=$(DOCKER_PASSWORD)

push-images:
	$(call _info, pushing docker images to registry)
	for image in $(IMAGES); \
	do make -C $$image push-image; \
	done
