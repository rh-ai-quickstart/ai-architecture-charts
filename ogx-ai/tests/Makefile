# Install and uninstall the ogx-ai integration test umbrella chart.
#
# Usage:
#   export HF_TOKEN=...
#   make install
#   make uninstall
#
# Optional overrides:
#   NAMESPACE=my-ns HF_TOKEN=... make install
#   DEVICE=gpu HF_TOKEN=... make install
#   HELM_EXTRA_ARGS='--set ingestion-pipeline.enabled=false' HF_TOKEN=... make install

RELEASE_NAME ?= ogx-ai-test
CHART_DIR      := .
VALUES_FILE    := values.yaml
DEVICE         ?= cpu
KUBECTL        ?= oc
HELM           ?= helm

ifneq ($(NAMESPACE),)
HELM_NS_ARGS   := --namespace $(NAMESPACE)
KUBECTL_NS_ARGS := -n $(NAMESPACE)
endif

.PHONY: install uninstall deps

deps:
	$(HELM) dependency update $(CHART_DIR)

install: deps
ifndef HF_TOKEN
	$(error HF_TOKEN is required — export it or pass HF_TOKEN=... on the command line)
endif
	$(HELM) upgrade --install $(RELEASE_NAME) $(CHART_DIR) \
		-f $(VALUES_FILE) \
		$(HELM_NS_ARGS) \
		--set llm-service.device=$(DEVICE) \
		--set llm-service.secret.hf_token="$(HF_TOKEN)" \
		$(HELM_EXTRA_ARGS)

uninstall:
	-$(HELM) uninstall $(RELEASE_NAME) $(HELM_NS_ARGS)
	$(KUBECTL) delete pvc ogx-ai-data pgvector-pg-data $(KUBECTL_NS_ARGS) --ignore-not-found
