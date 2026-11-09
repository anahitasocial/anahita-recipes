# The commons recipe's tasks, each one word. `make` alone lists them.
#
# The site's own values are in site.env, which `make init` writes. Every
# kubectl names the site's own kubeconfig and context, never the default
# one, so that nothing here can touch another cluster.

-include site.env

# The version of Anahita the site runs: newTag in k8s/kustomization.yml,
# which `make upgrade` changes, with ref= beside it.
ANAHITA_VERSION := $(shell sed -n 's/^ *newTag: //p' k8s/kustomization.yml | head -1)
K3S_VERSION ?= v1.37.1+k3s1
CERT_MANAGER_VERSION ?= v1.21.3

KUBECONFIG_FILE ?= $(HOME)/.kube/$(DOMAIN).yaml
TUNNEL_PORT ?= 16443
KUBECTL = kubectl --kubeconfig $(KUBECONFIG_FILE) --context $(DOMAIN)
export K3S_VERSION CERT_MANAGER_VERSION ANAHITA_VERSION TUNNEL_PORT

.DEFAULT_GOAL := help
.PHONY: help init site server tunnel tunnel-open status pods apply build publish web restart logs backup mail-off mail-on upgrade

## help: this list
help:
	@sed -n 's/^## //p' $(MAKEFILE_LIST) | awk -F': ' '{ printf "  %-10s %s\n", $$1, substr($$0, length($$1) + 3) }'

## init: asks for the domain, the mail and the server, and makes every key; once only
init:
	@scripts/init.sh

# Stops with a plain answer before init has been run.
site:
	@test -n "$(DOMAIN)" -a -n "$(SERVER)" || { echo "Run 'make init' first."; exit 1; }

## server: readies a new Ubuntu server over SSH (swap, k3s, cert-manager) and brings its kubeconfig here
server: site
	scripts/server.sh $(SSH_USER)@$(SERVER) $(KUBECONFIG_FILE) $(DOMAIN)

## tunnel: opens the way to the cluster over SSH, on 127.0.0.1:16443, while it runs
# Kubernetes' own port, 6443, is never opened to the internet: it is
# reached through SSH, which is.
tunnel: site
	@echo "The tunnel is open while this runs. Use another terminal; Ctrl-C closes it."
	ssh -N -L $(TUNNEL_PORT):127.0.0.1:6443 $(SSH_USER)@$(SERVER)

# Stops with a plain answer when the tunnel is not open.
tunnel-open: site
	@nc -z 127.0.0.1 $(TUNNEL_PORT) 2>/dev/null || { \
	  echo "The tunnel is not open. Run 'make tunnel' in a terminal of its own, then again."; exit 1; }

## status: the site's pods, and how much of the server is in use
status: tunnel-open
	$(KUBECTL) -n anahita get pods
	@$(KUBECTL) top nodes 2>/dev/null || true

## pods: every pod on the server, k3s's own too (Traefik, CoreDNS, cert-manager)
pods: tunnel-open
	$(KUBECTL) get pods -A

## apply: puts k8s/ in place, the first time, after a change to config.env, or after an upgrade
# The two Jobs, the database's migrations and Garage's setup, are made again
# each time: a Job cannot be changed once made. A finished one is removed
# first, and never one still running.
apply: tunnel-open
	@test -f k8s/secrets.env || { echo "There is no k8s/secrets.env: run 'make init' first."; exit 1; }
	@for job in migration-job garage-init; do \
	  if [ -n "$$($(KUBECTL) -n anahita get job $$job -o jsonpath='{.status.active}' 2>/dev/null)" ]; then \
	    echo "$$job is still running. Wait for it (make status), then again."; exit 1; fi; \
	  $(KUBECTL) -n anahita delete job $$job --ignore-not-found; \
	done
	$(KUBECTL) apply -k k8s

## build: builds the web app into web/build/, from anahita-web at REF (main unless said)
build: site
	web/build.sh $(REF)

## publish: puts web/build/ live, and starts web-shell again
publish: tunnel-open
	web/publish.sh $(KUBECONFIG_FILE) $(DOMAIN)

## web: build, then publish
web: build publish

## restart: starts a service again, SERVICE=web-shell for example
restart: tunnel-open
	@test -n "$(SERVICE)" || { echo "Name it: make restart SERVICE=web-shell"; exit 1; }
	$(KUBECTL) -n anahita rollout restart deployment/$(SERVICE)

## logs: the last hour of a service's log, SERVICE=auth-service for example
logs: tunnel-open
	@test -n "$(SERVICE)" || { echo "Name it: make logs SERVICE=auth-service"; exit 1; }
	$(KUBECTL) -n anahita logs deployment/$(SERVICE) --since=1h

## backup: copies the database into the files now, as is done every night at 03:30 UTC
backup: tunnel-open
	$(KUBECTL) -n anahita create job --from=cronjob/mysql-backup mysql-backup-$$(date -u +%Y%m%d-%H%M%S)

## mail-off: stops every email the site sends, at once (mail-on, or apply, sends again)
mail-off: tunnel-open
	$(KUBECTL) -n anahita scale deployment mail-grpc-service --replicas=0

## mail-on: sends email again
mail-on: tunnel-open
	$(KUBECTL) -n anahita scale deployment mail-grpc-service --replicas=1

# The version follows the word upgrade, as in make upgrade v1.2.4: it is
# not a target of its own. VERSION= works too.
ifeq (upgrade,$(firstword $(MAKECMDGOALS)))
ifneq (,$(word 2,$(MAKECMDGOALS)))
VERSION := $(word 2,$(MAKECMDGOALS))
$(eval $(VERSION):;@:)
endif
endif

## upgrade: names another version of Anahita, as in make upgrade v1.2.4; then make apply
# Read what the version needs first, in anahita-services' CHANGELOG.md.
upgrade:
	@test -n "$(VERSION)" || { echo "Name it: make upgrade v1.2.4 (now $(ANAHITA_VERSION))"; exit 1; }
	@echo "$(VERSION)" | grep -qE '^v[0-9]+\.[0-9]+\.[0-9]+$$' || { echo "A version looks like v1.2.4."; exit 1; }
	perl -pi -e 's/\Q$(ANAHITA_VERSION)\E/$(VERSION)/g' k8s/kustomization.yml
	@echo "k8s/kustomization.yml names $(VERSION). Read what it needs:"
	@echo "  https://github.com/anahitasocial/anahita-services/blob/$(VERSION)/CHANGELOG.md"
	@echo "then make apply."
