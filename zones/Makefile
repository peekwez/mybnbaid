run-wheel-builder:
	docker run --rm \
	-v "$$(pwd)":/application \
	-v "$$(pwd)/wheelhouse":/wheelhouse \
	-v "$(ROOT)/dependencies":/dependencies \
	$(PROJECT).builder;

build-image:
	docker build -t $(PROJECT).zones:$(TAG) -f docker.run .;

push-image:
	docker push $(PROJECT).zones:$(TAG)

install-service:
	python setup.py install 
	rm -fr build/ dist/
	rm -fr mybnbaid_zones.egg-info

start-service:
	./run.sh