.DEFAULT_GOAL := help
Name := ${Name}
Env := ${Env}
Stackname := $(Name)-$(Env)
S3BucketName := ${S3BucketName}

## sam build
build:
	sam build --use-container

## Deploy
deploy: build
	sam deploy \
		--stack-name $(Stackname) \
		--s3-prefix $(Stackname) \
		--s3-bucket $(S3BucketName) \
		--no-fail-on-empty-changeset \
		--parameter-overrides "Name=$(Name)" "Env=$(Env)"

## Deploy confirm-changeset
deploy_confirm_changeset: build
	sam deploy \
		--stack-name $(Stackname) \
		--s3-prefix $(Stackname) \
		--s3-bucket $(S3BucketName) \
		--no-fail-on-empty-changeset \
		--parameter-overrides "Name=$(Name)" "Env=$(Env)" \
		--confirm-changeset

## Show help
help:
	@make2help $(MAKEFILE_LIST)

.PHONY: help
.SILENT:
