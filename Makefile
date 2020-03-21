TAG ?= dev
PROJECT ?= mybnbaid
ROOT ?= ${CURDIR}
export

NAME := xyz
IMAGES := users zones properties mail sms gateway
SERVICES := users zones properties mail sms gateway
DEPS := schemaless rock


.PHONY = logs dependencies install supervisor

build: build-images

push: push-images


create:
	rock.service -d $(ROOT) -s $(NAME)
	chmod a+x $(ROOT)/$(NAME)/run.sh
	git add $(NAME)/*

dependencies:
	for dep in $(DEPS); \
	do make -C dependencies/$$dep install;
	done

install: dependencies
	for service in $(SERVICES); \
	do make -C $$service install-service; \
	done

prune:
	docker system prune

network:
	docker network create \
	--driver=bridge \
	--subnet=192.168.0.0/24 \
	--gateway=192.168.0.1 \
	$(PROJECT)

compose:
	docker-compose up -d --remove-orphans $(SERVICES)

logs:
	rm -fr logs 
	mkdir logs
	touch logs/supervisord.log logs/access.log logs/error.log
	for service in $(SERVICES); \
	do touch logs/$$service.broker.log logs/$$service.service.log; done

initdb:
	rock.syncdb -c datastore.yml

supervisor:
	rock.supervisor -c services.yml

start: install logs supervisor
	sleep 5
	supervisord -c supervisord.conf

stop:
	supervisorctl -u mybnbaid -p password stop all
	supervisorctl -u mybnbaid -p password shutdown

status:
	supervisorctl -u mybnbaid -p password status

build-base:
	docker build -t $(PROJECT).base \
	-f docker/docker.base .

build-wheel-builder: build-base
	docker build -t $(PROJECT).builder \
	-f docker/docker.build .

run-wheel-builder: build-wheel-builder
	for image in $(IMAGES); \
	do make -C $$image run-wheel-builder; \
	done

build-images: run-wheel-builder
	for image in $(IMAGES); \
	do make -C $$image build-image; \
	done

docker-login:
	docker login --username=$(DOCKER_USERNAME) \
	--password=$(DOCKER_PASSWORD)

push-images:
	for image in $(IMAGES); \
	do make -C $$image push-image; \
	done
