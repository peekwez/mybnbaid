TAG ?= dev
PROJECT ?= mybnbaid
ROOT ?= ${CURDIR}
export

NAME := xyz
IMAGES := users
SERVICE := users

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
