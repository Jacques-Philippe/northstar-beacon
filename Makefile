# Beacon — local targets.
#
# Image tags are the immutable git short SHA (never `latest`, per CLAUDE.md). Build from a
# clean tree so the tag matches what's committed.

IMAGE          ?= beacon
FRONTEND_IMAGE ?= beacon-frontend
SHA            := $(shell git rev-parse --short HEAD)
TAG            := $(IMAGE):$(SHA)
FRONTEND_TAG   := $(FRONTEND_IMAGE):$(SHA)

KIND_CLUSTER := beacon-dev

# Pinned so `make ingress-up` is reproducible — never point this at a mutable branch ref.
INGRESS_NGINX_VERSION := controller-v1.11.3

.PHONY: image frontend-image run-api run-checker run-frontend dev-up dev-down ingress-up kind-load deploy-dev dev-status

## Build the api/checker container image, tagged with the current git short SHA.
image:
	docker build -t $(TAG) .
	@echo "built $(TAG)"

## Build the frontend container image, tagged with the current git short SHA.
frontend-image:
	docker build -t $(FRONTEND_TAG) frontend/
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

## Create the beacon-dev kind cluster (needs `kind` on PATH: brew install kind) and
## install the ingress controller into it.
dev-up:
	kind create cluster --name $(KIND_CLUSTER) --config kind/dev.yaml
	$(MAKE) ingress-up
	@echo
	@echo "Add this to /etc/hosts if it isn't there yet:"
	@echo "  127.0.0.1 beacon.dev.local"

## Delete the beacon-dev cluster.
dev-down:
	kind delete cluster --name $(KIND_CLUSTER)

## Install ingress-nginx into beacon-dev (kind's own deploy manifest — it already targets
## nodes labelled ingress-ready=true, which kind/dev.yaml sets) and wait for the controller
## to be ready. Waits on the Deployment, not a pod selector: right after apply there may be
## no matching Pod yet, and `kubectl wait` on a selector that matches nothing errors
## immediately instead of retrying — the Deployment object exists as soon as apply returns.
ingress-up:
	kubectl --context kind-$(KIND_CLUSTER) apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/$(INGRESS_NGINX_VERSION)/deploy/static/provider/kind/deploy.yaml
	kubectl --context kind-$(KIND_CLUSTER) wait --namespace ingress-nginx \
		--for=condition=available --timeout=120s \
		deployment/ingress-nginx-controller

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
