db = schemaless -d users
sc = -s users
cmd = -c create

run-wheel-builder:
	docker run --rm \
	-v "$$(pwd)":/application \
	-v "$$(pwd)/wheelhouse":/wheelhouse \
	-v "$(ROOT)/dependencies":/dependencies \
	$(PROJECT).builder;

build-image:
	docker build -t $(PROJECT).users:$(TAG) -f docker.run .;

push-image:
	docker push $(PROJECT).users:$(TAG)

install-service:
	python setup.py install 
	rm -fr build/ dist/
	rm -fr mybnbaid_users.egg-info

start-service:
	./run.sh
