SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
MAKEFLAGS += --no-builtin-rules

ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
SYNC_CMD := $(ROOT_DIR)/scripts/sync-project.sh
DOWN_CMD := $(ROOT_DIR)/scripts/run/down.sh
INSTALL_UNITS_CMD := $(ROOT_DIR)/scripts/install/systemd-user-units.sh

SYNC_SERVICES := \
	tts:apps/qwen_tts_api \
	asr:apps/qwen_asr_api \
	deepseek:apps/ocr_deepseek_api \
	ocr:apps/ocr_glm_api \
	ocr-gateway:apps/ocr_gateway

RUN_SERVICES := \
	tts:$(ROOT_DIR)/scripts/run/qwen-tts.sh \
	tts-clone:$(ROOT_DIR)/scripts/run/qwen-tts-clone.sh \
	asr:$(ROOT_DIR)/scripts/run/qwen-asr.sh \
	deepseek:$(ROOT_DIR)/scripts/run/deepseek-ocr2.sh \
	ocr:$(ROOT_DIR)/scripts/run/glm-ocr.sh \
	ocr-gateway:$(ROOT_DIR)/scripts/run/ocr-gateway.sh

HEALTH_SERVICES := \
	tts:8002 \
	tts-clone:8004 \
	asr:8003 \
	deepseek:8010 \
	ocr:8011 \
	ocr-gateway:8012

SYNC_TARGETS := $(addprefix sync-,$(foreach entry,$(SYNC_SERVICES),$(word 1,$(subst :, ,$(entry)))))
RUN_TARGETS := $(foreach entry,$(RUN_SERVICES),$(word 1,$(subst :, ,$(entry))))
ALIAS_TARGETS := sync-tts-clone ocr-glm

.PHONY: help sync-all all down health install-user-units $(SYNC_TARGETS) $(RUN_TARGETS) $(ALIAS_TARGETS)

help:
	@printf '%s\n' \
		"Sync: $(SYNC_TARGETS)" \
		"Run: $(RUN_TARGETS)" \
		"Meta: sync-all | all | down | health | install-user-units" \
		"Aliases: sync-tts-clone -> sync-tts, ocr-glm -> ocr"

define DEFINE_SYNC_TARGET
sync-$(word 1,$(subst :, ,$(1))):
	@bash -lc "$(SYNC_CMD) $(word 2,$(subst :, ,$(1)))"
endef

$(foreach entry,$(SYNC_SERVICES),$(eval $(call DEFINE_SYNC_TARGET,$(entry))))

define DEFINE_RUN_TARGET
$(word 1,$(subst :, ,$(1))):
	@bash -lc "$(word 2,$(subst :, ,$(1)))"
endef

$(foreach entry,$(RUN_SERVICES),$(eval $(call DEFINE_RUN_TARGET,$(entry))))

sync-tts-clone: sync-tts

ocr-glm: ocr

sync-all:
	@$(MAKE) --no-print-directory $(SYNC_TARGETS)

all:
	@$(MAKE) --no-print-directory -j$(words $(RUN_TARGETS)) $(RUN_TARGETS)

down:
	@bash -lc "$(DOWN_CMD)"

health:
	@status=0; \
	for entry in $(HEALTH_SERVICES); do \
		service="$${entry%%:*}"; \
		port="$${entry##*:}"; \
		printf '%s ' "$$service"; \
		if ! curl -fsS --max-time 5 "http://localhost:$$port/health"; then \
			status=1; \
		fi; \
		printf '\n'; \
	done; \
	exit $$status

install-user-units:
	@bash -lc "$(INSTALL_UNITS_CMD)"
