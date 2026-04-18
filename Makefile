REGISTRY  ?= docker.io/youruser
IMAGE     ?= copiousbags-monitor
VERSION   ?= $(shell git rev-parse --short HEAD 2>/dev/null || echo "latest")
FULL_TAG   = $(REGISTRY)/$(IMAGE):$(VERSION)
LATEST_TAG = $(REGISTRY)/$(IMAGE):latest

.PHONY: build up down logs check clean push release

## Build the monitor image
build:
	docker compose build

## Start all services in the background
up:
	docker compose up -d

## Stop all services
down:
	docker compose down

## Stream monitor logs
logs:
	docker compose logs -f monitor

## Run a one-off check (starts services if needed, tails logs until exit)
check:
	docker compose up --build -d
	docker compose logs -f monitor

## Remove stopped containers and stale screenshots
clean:
	docker compose down --remove-orphans
	rm -f screenshots/*.png

## Build and tag the monitor image for the registry
image:
	docker build -t $(FULL_TAG) -t $(LATEST_TAG) .
	@echo "Tagged: $(FULL_TAG)"
	@echo "Tagged: $(LATEST_TAG)"

## Push versioned and latest tags to the registry
push: image
	docker push $(FULL_TAG)
	docker push $(LATEST_TAG)

## Build, tag and push in one step
release: push
	@echo "Released $(FULL_TAG)"

## Pull and run the monitor from the registry (no local build needed)
run:
	docker pull $(LATEST_TAG)
	docker run -d --name copiousbags-monitor \
		--env-file .env \
		-v $(PWD)/screenshots:/screenshots \
		--network host \
		$(LATEST_TAG)
