EIID_LOCAL_CONFIG ?= config/local.mk
-include $(EIID_LOCAL_CONFIG)

SIM_CONFIG ?= config/sim_config.json
RAW_ROOT_FILE ?= runs/raw_efficiency/raw_efficiency_master.root
ROOT_EXECUTABLE ?= $(dir $(ROOT_CONFIG))root

all: simulation

configure:
	bash configure.sh

check-config:
	@if test "$(EIID_LOCAL_CONFIGURED)" != "1"; then \
		echo "Error: dependency configuration is missing."; \
		echo "Run 'make configure' once, then rerun make."; \
		exit 1; \
	fi

simulation: check-config
	$(MAKE) -C Geant4_Simulation

run-simulation: simulation
	$(MAKE) -C Geant4_Simulation run SIM_CONFIG="$(SIM_CONFIG)"

quicklook: check-config
	@test -f "$(RAW_ROOT_FILE)" || { \
		echo "Error: missing $(RAW_ROOT_FILE). Run 'make run-simulation' first."; \
		exit 1; \
	}
	cd Quicklook && "$(ROOT_EXECUTABLE)" -l -b -q run_raw_efficiency_map.C

# 固定的小规模验收：28 个前半球方向，每个 10000 个 gamma，单能 0.662 MeV。
# 写入 runs/smoke_test，保留 runs/raw_efficiency 中已有的原始文件。
smoke: simulation
	$(MAKE) -C Geant4_Simulation run SIM_CONFIG=config/smoke_config.json
	"$(ROOT_EXECUTABLE)" -l -b -q 'Geant4_Simulation/tests/check_smoke_output.C("runs/smoke_test/raw_efficiency_master.root")'

smoke-plot: check-config
	@test -f runs/smoke_test/raw_efficiency_master.root || { echo "Run 'make smoke' first."; exit 1; }
	cd Quicklook && "$(ROOT_EXECUTABLE)" -l -b -q 'run_raw_efficiency_map.C("../runs/smoke_test/raw_efficiency_master.root", "figures/smoke_test")'

experiment:
	$(MAKE) run-simulation
	$(MAKE) quicklook

test: simulation
	$(MAKE) -C Geant4_Simulation test

clean:
	$(MAKE) -C Geant4_Simulation clean

.PHONY: all configure check-config simulation run-simulation quicklook \
	experiment test clean smoke smoke-plot
