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

setup-db:
	schemaless schema -c create -s users
	schemaless table -c create -s users -t users
	schemaless table -c create -s users -t address
	schemaless table -c create -s users -t blacklists
	schemaless index -c create -s users -t users -f email -dt str
	schemaless index -c create -s users -t address -f user_id -dt int64
	schemaless index -c create -s users -t address -f city -dt str
	schemaless index -c create -s users -t blacklists -f user_id -dt int64
	
start-service:
	./run.sh
