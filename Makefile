TAG ?= dev
PROJECT ?= mybnbaid
ROOT ?= ${CURDIR}
export

NAME := xyz
IMAGES := users mail gateway
SERVICE := users mail gateway
LOGS = supervisor gateway.service users.service mail.service users.queue mail.streamer


build: build-images

push: push-images


init:
	python sample/initsvc.py -d $(ROOT) -s $(NAME)
	chmod a+x $(ROOT)/$(NAME)/run.sh
	
prune:
	docker system prune

network:
	docker network create \
	--driver=bridge \
	--subnet=192.168.0.0/24 \
	--gateway=192.168.0.1 \
	$(PROJECT)

start:
	docker-compose up --remove-orphans $(SERVICE)

create-logs:
	rm -fr logs 
	mkdir logs
	for file in $(LOGS); \
	do touch logs/$$file.log ; done

start-procs: create-logs
	supervisord -c supervisord.conf

stop-procs:
	supervisorctl -u mybnbaid -p password stop all
	supervisorctl -u mybnbaid -p password shutdown

check-procs:
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

test:
	@echo ${ROOT}
