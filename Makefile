# Beacon — local targets.
#
# Image tags are the immutable git short SHA (never `latest`, per CLAUDE.md). Build from a
# clean tree so the tag matches what's committed.

IMAGE          ?= beacon
FRONTEND_IMAGE ?= beacon-frontend
SHA            := $(shell git rev-parse --short HEAD)
TAG            := $(IMAGE):$(SHA)
FRONTEND_TAG   := $(FRONTEND_IMAGE):$(SHA)

# Where the frontend build points its baked-in API calls — the beacon-dev port-forward
# for svc/beacon-api. Override per FRONTEND_API_URL if you forward a different port.
FRONTEND_API_URL ?= http://localhost:8000

KIND_CLUSTER := beacon-dev

.PHONY: image frontend-image run-api run-checker run-frontend dev-up dev-down kind-load deploy-dev dev-status

## Build the api/checker container image, tagged with the current git short SHA.
image:
	docker build -t $(TAG) .
	@echo "built $(TAG)"

## Build the frontend container image, tagged with the current git short SHA.
frontend-image:
	docker build --build-arg VITE_API_URL=$(FRONTEND_API_URL) -t $(FRONTEND_TAG) frontend/
	@echo "built $(FRONTEND_TAG)"

## Run the api entrypoint, API published on localhost:8000.
run-api: image
	docker run --rm -p 8000:8000 $(TAG) api

## Run the checker entrypoint.
run-checker: image
	docker run --rm $(TAG) checker

## Run the frontend image, page published on localhost:8080.
run-frontend: frontend-image
	docker run --rm -p 8080:80 $(FRONTEND_TAG)

# ---- kind / dev cluster -------------------------------------------------

## Create the beacon-dev kind cluster (needs `kind` on PATH: brew install kind).
dev-up:
	kind create cluster --name $(KIND_CLUSTER) --config kind/dev.yaml

## Delete the beacon-dev cluster.
dev-down:
	kind delete cluster --name $(KIND_CLUSTER)

## Build both images and side-load them into the kind node (kind has no registry access).
kind-load: image frontend-image
	kind load docker-image $(TAG) --name $(KIND_CLUSTER)
	kind load docker-image $(FRONTEND_TAG) --name $(KIND_CLUSTER)

## Point the dev overlay at the current SHA (both images) and apply it to beacon-dev.
deploy-dev: kind-load
	cd k8s/overlays/dev && sed -i.bak -E 's/^( *newTag: ).*/\1"$(SHA)"/' kustomization.yaml && rm kustomization.yaml.bak
	kubectl --context kind-$(KIND_CLUSTER) apply -k k8s/overlays/dev
	kubectl --context kind-$(KIND_CLUSTER) rollout status deployment/beacon-api
	kubectl --context kind-$(KIND_CLUSTER) rollout status deployment/beacon-frontend

## The get / describe / logs loop, in one place.
dev-status:
	kubectl --context kind-$(KIND_CLUSTER) get deploy,rs,pod,svc -l app=beacon
