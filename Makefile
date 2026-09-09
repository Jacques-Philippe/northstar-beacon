# Beacon — local targets.
#
# Image tags are the immutable git short SHA (never `latest`, per CLAUDE.md). Build from a
# clean tree so the tag matches what's committed.

IMAGE ?= beacon
SHA   := $(shell git rev-parse --short HEAD)
TAG   := $(IMAGE):$(SHA)

KIND_CLUSTER := beacon-dev

.PHONY: image run-api run-checker dev-up dev-down kind-load deploy-dev dev-status

## Build the container image, tagged with the current git short SHA.
image:
	docker build -t $(TAG) .
	@echo "built $(TAG)"

## Run the api entrypoint, API published on localhost:8000.
run-api: image
	docker run --rm -p 8000:8000 $(TAG) api

## Run the checker entrypoint.
run-checker: image
	docker run --rm $(TAG) checker

# ---- kind / dev cluster (Beat 1.3) -------------------------------------------------

## Create the beacon-dev kind cluster (needs `kind` on PATH: brew install kind).
dev-up:
	kind create cluster --name $(KIND_CLUSTER) --config kind/dev.yaml

## Delete the beacon-dev kind cluster.
dev-down:
	kind delete cluster --name $(KIND_CLUSTER)

## Build the image and load it into the kind node (kind has no registry access).
kind-load: image
	kind load docker-image $(TAG) --name $(KIND_CLUSTER)

## Point the dev overlay at the current SHA and apply it to beacon-dev.
deploy-dev: kind-load
	cd k8s/overlays/dev && sed -i.bak -E 's/^( *newTag: ).*/\1$(SHA)/' kustomization.yaml && rm kustomization.yaml.bak
	kubectl --context kind-$(KIND_CLUSTER) apply -k k8s/overlays/dev
	kubectl --context kind-$(KIND_CLUSTER) rollout status deployment/beacon-api

## The get / describe / logs loop, in one place.
dev-status:
	kubectl --context kind-$(KIND_CLUSTER) get deploy,rs,pod,svc -l app=beacon
