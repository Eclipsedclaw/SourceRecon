EIID_LOCAL_CONFIG ?= config/local.mk
-include $(EIID_LOCAL_CONFIG)

MODULES := common Reconstruction GridResampler Geant4_Simulation Translator Visualization
SIM_CONFIG ?= config/sim_config.json

all: v5-all

configure:
	bash configure.sh

check-config:
	@if test "$(EIID_LOCAL_CONFIGURED)" != "1"; then \
		echo "Error: dependency configuration is missing."; \
		echo "Run 'make configure' once, then rerun make."; \
		exit 1; \
	fi

show-config: check-config
	@echo "CXX=$(CXX)"
	@echo "PROJECT_CXX_STANDARD=$(PROJECT_CXX_STANDARD)"
	@echo "ROOT_CONFIG=$(ROOT_CONFIG)"
	@echo "GEANT4_CONFIG=$(GEANT4_CONFIG)"
	@echo "EIID_HAVE_GEANT4=$(EIID_HAVE_GEANT4)"
	@echo "HEALPIX_CFLAGS=$(HEALPIX_CFLAGS)"
	@echo "HEALPIX_LIBS=$(HEALPIX_LIBS)"

common: check-config
	$(MAKE) -C common

reconstruction: check-config common
	$(MAKE) -C Reconstruction

resampler: check-config common
	$(MAKE) -C GridResampler

simulation: check-config
	$(MAKE) -C Geant4_Simulation

run-simulation: simulation
	$(MAKE) -C Geant4_Simulation run SIM_CONFIG="$(SIM_CONFIG)"

translator: check-config
	$(MAKE) -C Translator

visualization: check-config
	$(MAKE) -C Visualization

EIID_Recon_V5: reconstruction
grid_resampler: resampler
geant4_simulator: simulation
eiid_translator: translator
eiid_plotter: visualization

v5-all: check-config reconstruction resampler simulation translator visualization

test:
	$(MAKE) -C common test
	$(MAKE) -C Reconstruction test
	$(MAKE) -C Geant4_Simulation test

clean:
	@for module in $(MODULES); do \
		$(MAKE) -C $$module clean || exit $$?; \
	done

help:
	@echo "make common          Build the shared C++ library."
	@echo "make configure       Discover dependencies and write config/local.mk."
	@echo "make show-config     Print the active compiler and dependency configuration."
	@echo "make reconstruction  Build Reconstruction/EIID_Recon_V5."
	@echo "make resampler       Build GridResampler/grid_resampler."
	@echo "make simulation      Build Geant4_Simulation/geant4_simulator."
	@echo "make run-simulation  Initialize Geant4 and run the simulator."
	@echo "make translator      Build Translator/eiid_translator."
	@echo "make visualization   Build Visualization/eiid_plotter."
	@echo "make v5-all          Build every V5 executable."
	@echo "make test            Run dependency-light unit tests."
	@echo "make clean           Clean every module."

.PHONY: all configure check-config show-config common reconstruction resampler simulation run-simulation translator \
	visualization EIID_Recon_V5 grid_resampler geant4_simulator \
	eiid_translator eiid_plotter v5-all test clean help
