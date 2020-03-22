TAG ?=dev
PROJECT ?=mybnbaid
ROOT ?=${CURDIR}
export

# service variables
NAME ?=xyz
SERVICES ?=users zones properties mail sms gateway
DEPS ?=schemaless rock

# AWS secrets manager and JSON parser for response
JSON =jq -r
SM_ARGS =SecretString
GET_SECRET =aws secretsmanager get-secret-value --secret-id

# DB secret and connection variables
KEY ?=DEV_DBS
FIELD ?=general
DB ?=testdb

include Make.in

.PHONY: secrets logs dependencies 

build: build-images

push: push-images

check-db-config: secrets
	psql $(DSN) -c "SELECT * FROM public.tables;" 
	psql $(DSN) -c "SELECT * FROM public.indexes;" 

close-conn:
	$(call _info, closing connections to $(DB) database)
	psql $(DSN) -c "SELECT pg_terminate_backend(pid) \
	FROM pg_stat_activity WHERE datname='$(DB)'"

drop-db:
	$(call _info, dropping $(DB) database)
	psql $(DSN) -c "DROP DATABASE IF EXISTS $(DB);"

create-db: secrets closeconn dropdb
	$(call _info, creating $(DB) database)
	psql $(DSN) -c "CREATE DATABASE $(DB);"

secrets:
	$(call _info, fetching secret from aws secrets manager)
	$(eval DSN = $(shell $(GET_SECRET) $(KEY) | $(JSON) ".$(SM_ARGS)" | $(JSON) ".$(FIELD)"))

create:
	$(call _info, initializing a service template)
	rock.service -d $(ROOT) -s $(NAME)
	chmod a+x $(ROOT)/$(NAME)/run.sh
	git add $(NAME)/*

dependencies:
	$(call _info, installing project dependencies)
	for dep in $(DEPS); \
	do make -C dependencies/$$dep install;
	done

install: dependencies
	$(call _info, installing project services)
	for service in $(SERVICES); \
	do make -C $$service install-service; \
	done

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
	rm -fr logs 
	mkdir logs
	touch logs/supervisord.log logs/access.log logs/error.log
	for service in $(SERVICES); \
	do touch logs/$$service.broker.log logs/$$service.service.log; done

initdb:
	$(call _info, initializing service databases)
	rock.syncdb -c datastore.yml

supervisor:
	$(call _info, creating supervisor configuration for services)
	rock.supervisor -c services.yml

start: install logs supervisor
	$(call _info, starting service processes)
	sleep 5
	supervisord -c supervisord.conf

stop:
	$(call _info, stopping service processes)
	supervisorctl -u mybnbaid -p password stop all
	supervisorctl -u mybnbaid -p password shutdown

status:
	$(call _info, checking status of service processes)
	supervisorctl -u mybnbaid -p password status

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
