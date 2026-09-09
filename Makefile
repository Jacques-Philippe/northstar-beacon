# Beacon — local targets.
#
# Image tags are the immutable git short SHA (never `latest`, per CLAUDE.md). Build from a
# clean tree so the tag matches what's committed.

IMAGE ?= beacon
SHA   := $(shell git rev-parse --short HEAD)
TAG   := $(IMAGE):$(SHA)

.PHONY: image run-api run-checker

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
