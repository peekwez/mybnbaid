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

setup-db:
	$(db) config $(cmd)
	$(db) schema $(cmd) $(sc)
	$(db) table  $(cmd) $(sc) -t users
	$(db) table  $(cmd) $(sc) -t address
	$(db) table  $(cmd) $(sc) -t blacklists
	$(db) index  $(cmd) $(sc) -t users -f email -dt str
	$(db) index  $(cmd) $(sc) -t address -f user_id -dt int64
	$(db) index  $(cmd) $(sc) -t address -f city -dt str
	$(db) index  $(cmd) $(sc) -t blacklists -f user_id -dt int64
	
start-service:
	./run.sh
