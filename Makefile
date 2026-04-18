COPIOUS_DIR = copious
BLOOM_DIR   = bloom

.PHONY: \
	copious-build copious-up copious-down copious-logs copious-check copious-clean copious-image copious-push copious-release \
	bloom-build   bloom-up   bloom-down   bloom-logs   bloom-check   bloom-clean   bloom-image   bloom-push   bloom-release \
	up down logs clean

# ──────────────────────────────────────────
#  COPIOUS BAGS
# ──────────────────────────────────────────

## Build the copiousbags monitor image
copious-build:
	docker compose -f $(COPIOUS_DIR)/docker-compose.yml --project-directory $(COPIOUS_DIR) build

## Start copiousbags monitor in the background
copious-up:
	docker compose -f $(COPIOUS_DIR)/docker-compose.yml --project-directory $(COPIOUS_DIR) up -d

## Stop copiousbags monitor
copious-down:
	docker compose -f $(COPIOUS_DIR)/docker-compose.yml --project-directory $(COPIOUS_DIR) down

## Stream copiousbags monitor logs
copious-logs:
	docker compose -f $(COPIOUS_DIR)/docker-compose.yml --project-directory $(COPIOUS_DIR) logs -f monitor

## Build + start + tail copiousbags logs
copious-check:
	docker compose -f $(COPIOUS_DIR)/docker-compose.yml --project-directory $(COPIOUS_DIR) up --build -d
	docker compose -f $(COPIOUS_DIR)/docker-compose.yml --project-directory $(COPIOUS_DIR) logs -f monitor

## Remove copiousbags containers and screenshots
copious-clean:
	docker compose -f $(COPIOUS_DIR)/docker-compose.yml --project-directory $(COPIOUS_DIR) down --remove-orphans
	rm -f $(COPIOUS_DIR)/screenshots/*.png

## Build and tag copiousbags image for registry
copious-image:
	docker build -t docker.io/thiagousa/copiousbags-monitor:latest $(COPIOUS_DIR)

## Push copiousbags image to registry
copious-push: copious-image
	docker push docker.io/thiagousa/copiousbags-monitor:latest

## Build, tag and push copiousbags in one step
copious-release: copious-push
	@echo "Released copiousbags-monitor"

# ──────────────────────────────────────────
#  BLOOM BIRTH STUDIO
# ──────────────────────────────────────────

## Build the bloom monitor image
bloom-build:
	docker compose -f $(BLOOM_DIR)/docker-compose.yml --project-directory $(BLOOM_DIR) build

## Start bloom monitor in the background
bloom-up:
	docker compose -f $(BLOOM_DIR)/docker-compose.yml --project-directory $(BLOOM_DIR) up -d

## Stop bloom monitor
bloom-down:
	docker compose -f $(BLOOM_DIR)/docker-compose.yml --project-directory $(BLOOM_DIR) down

## Stream bloom monitor logs
bloom-logs:
	docker compose -f $(BLOOM_DIR)/docker-compose.yml --project-directory $(BLOOM_DIR) logs -f monitor

## Build + start + tail bloom logs
bloom-check:
	docker compose -f $(BLOOM_DIR)/docker-compose.yml --project-directory $(BLOOM_DIR) up --build -d
	docker compose -f $(BLOOM_DIR)/docker-compose.yml --project-directory $(BLOOM_DIR) logs -f monitor

## Remove bloom containers and screenshots
bloom-clean:
	docker compose -f $(BLOOM_DIR)/docker-compose.yml --project-directory $(BLOOM_DIR) down --remove-orphans
	rm -f $(BLOOM_DIR)/screenshots/*.png

## Build and tag bloom image for registry
bloom-image:
	docker build -t docker.io/thiagousa/bloombirthstudio-monitor:latest $(BLOOM_DIR)

## Push bloom image to registry
bloom-push: bloom-image
	docker push docker.io/thiagousa/bloombirthstudio-monitor:latest

## Build, tag and push bloom in one step
bloom-release: bloom-push
	@echo "Released bloombirthstudio-monitor"

# ──────────────────────────────────────────
#  BOTH SITES
# ──────────────────────────────────────────

## Start both monitors
up: copious-up bloom-up

## Stop both monitors
down: copious-down bloom-down

## Stream logs for both monitors (requires tmux or two terminals)
logs:
	@echo "Run in separate terminals:"
	@echo "  make copious-logs"
	@echo "  make bloom-logs"

## Clean both monitors
clean: copious-clean bloom-clean
