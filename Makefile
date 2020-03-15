TAG ?= dev
PROJECT ?= mybnbaid
ROOT ?= ${CURDIR}
export

NAME := xyz
IMAGES := users zones mail sms gateway
SERVICES := users zones mail sms gateway
LOGS = supervisor circus gateway.service users.service \
	mail.service users.queue mail.streamer \
	sms.service sms.streamer zones.queue \
	zones.service


build: build-images

push: push-images


init:
	python sample/initsvc.py -d $(ROOT) -s $(NAME)
	chmod a+x $(ROOT)/$(NAME)/run.sh
	
install:
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
	for file in $(LOGS); \
	do touch logs/$$file.log ; done

supervisor:
	rock.supervisor -c config.yml

start: install logs
	rock.supervisor -c config.yml
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
