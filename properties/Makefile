db = schemaless -d properties
sc = -s properties
cmd = -c create

run-wheel-builder:
	docker run --rm \
	-v "$$(pwd)":/application \
	-v "$$(pwd)/wheelhouse":/wheelhouse \
	-v "$(ROOT)/dependencies":/dependencies \
	$(PROJECT).builder;

build-image:
	docker build -t $(PROJECT).properties:$(TAG) -f docker.run .;

push-image:
	docker push $(PROJECT).properties:$(TAG)

install-service:
	python setup.py install 
	rm -fr build/ dist/
	rm -fr mybnbaid_properties.egg-info

start-service:
	./run.sh
