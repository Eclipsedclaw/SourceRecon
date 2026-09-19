EIID_LOCAL_CONFIG ?= config/local.mk
-include $(EIID_LOCAL_CONFIG)

MODULES := common PixelIntegration SimulationSupport ResponseKernel \
	Reconstruction GridResampler Geant4_Simulation Translator Visualization \
	DopplerSampleGenerator ResponseCalibration KernelBenchmark

SIM_CONFIG ?= config/sim_config.json
RESAMPLER_CONFIG ?= GridResampler/config/resampler_config.json
RESAMPLER_NSIDE8_CONFIG := GridResampler/config/resampler_nside8.json
RESAMPLER_NSIDE16_CONFIG := GridResampler/config/resampler_nside16.json
RESAMPLER_NSIDE32_CONFIG := GridResampler/config/resampler_nside32.json
CALIBRATION_CONFIG ?= ResponseCalibration/config/calibration_config.json
CENTER_RECON_CONFIG := Reconstruction/config/recon_center_nside8_i10.json
INTEGRATED_16_32_I10_CONFIG := Reconstruction/config/recon_integrated_nside16_32_i10.json
INTEGRATED_32_64_I10_CONFIG := Reconstruction/config/recon_integrated_nside32_64_i10.json
INTEGRATED_32_64_I20_CONFIG := Reconstruction/config/recon_integrated_nside32_64_i20.json
DEFAULT_RECON_CONFIG ?= Reconstruction/config/recon_config.json
BENCHMARK_CONFIG ?= KernelBenchmark/config/benchmark_config.json
MODEL_STATUS_JSON := runs/latest/calibration/model_status.json
PREFERRED_KERNEL := gaussian_lorentzian_mixture

all: v10-all

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

pixel-integration: check-config common
	$(MAKE) -C PixelIntegration

simulation-support: check-config
	$(MAKE) -C SimulationSupport

response-kernel: check-config
	$(MAKE) -C ResponseKernel

reconstruction: check-config common pixel-integration response-kernel
	$(MAKE) -C Reconstruction

resampler: check-config common
	$(MAKE) -C GridResampler

simulation: check-config
	$(MAKE) -C Geant4_Simulation

translator: check-config
	$(MAKE) -C Translator

visualization: check-config
	$(MAKE) -C Visualization

sample-generator: check-config simulation-support
	$(MAKE) -C DopplerSampleGenerator

response-calibration: check-config simulation-support
	$(MAKE) -C ResponseCalibration

kernel-benchmark: check-config
	$(MAKE) -C KernelBenchmark

# events.root is supplied by the user. V10 validates it before archiving an old
# run or starting any expensive simulation, and never writes this file.
validate-events: reconstruction
	./Reconstruction/EIID_Recon_V10 --validate-events-only $(CENTER_RECON_CONFIG)

prepare-run:
	bash scripts/prepare_run.sh

run-simulation: simulation
	$(MAKE) -C Geant4_Simulation run SIM_CONFIG="$(SIM_CONFIG)"

run-resampler: resampler
	./GridResampler/grid_resampler $(RESAMPLER_CONFIG)

run-resampler-all: resampler
	./GridResampler/grid_resampler $(RESAMPLER_NSIDE8_CONFIG)
	./GridResampler/grid_resampler $(RESAMPLER_NSIDE16_CONFIG)
	./GridResampler/grid_resampler $(RESAMPLER_NSIDE32_CONFIG)

run-sample-grid: sample-generator
	$(MAKE) -C DopplerSampleGenerator run-calibration-grid

calibrate: response-calibration
	./ResponseCalibration/response_calibrator $(CALIBRATION_CONFIG)

check-response-ready: response-calibration
	@test -f "$(MODEL_STATUS_JSON)" || { \
		echo "Error: missing $(MODEL_STATUS_JSON). Run 'make calibrate' first."; \
		exit 1; \
	}
	@./ResponseCalibration/response_calibrator \
		--model-usable "$(MODEL_STATUS_JSON)" $(PREFERRED_KERNEL)

reconstruct-center: reconstruction check-response-ready
	./Reconstruction/EIID_Recon_V10 $(CENTER_RECON_CONFIG)

reconstruct-integrated-16: reconstruction check-response-ready
	./Reconstruction/EIID_Recon_V10 $(INTEGRATED_16_32_I10_CONFIG)

reconstruct-integrated-32: reconstruction check-response-ready
	./Reconstruction/EIID_Recon_V10 $(INTEGRATED_32_64_I10_CONFIG)

reconstruct-iteration-20: reconstruction check-response-ready
	./Reconstruction/EIID_Recon_V10 $(INTEGRATED_32_64_I20_CONFIG)

reconstruct-default: reconstruction check-response-ready
	./Reconstruction/EIID_Recon_V10 $(DEFAULT_RECON_CONFIG)

reconstruct-pixel-study: reconstruction check-response-ready
	$(MAKE) reconstruct-center
	$(MAKE) reconstruct-integrated-16
	$(MAKE) reconstruct-integrated-32
	$(MAKE) reconstruct-iteration-20

benchmark: kernel-benchmark
	./KernelBenchmark/kernel_benchmark $(BENCHMARK_CONFIG)

visualize-center: visualization
	./Visualization/eiid_plotter Visualization/config/plot_center_nside8_i10.json

visualize-integrated-16: visualization
	./Visualization/eiid_plotter Visualization/config/plot_integrated_nside16_32_i10.json

visualize-integrated-32: visualization
	./Visualization/eiid_plotter Visualization/config/plot_integrated_nside32_64_i10.json

visualize-iteration-20: visualization
	./Visualization/eiid_plotter Visualization/config/plot_integrated_nside32_64_i20.json

visualize-pixel-study: visualization
	$(MAKE) visualize-center
	$(MAKE) visualize-integrated-16
	$(MAKE) visualize-integrated-32
	$(MAKE) visualize-iteration-20

# Complete, reproducible V10 study. It deliberately starts from the external
# events.root and produces all other data under runs/latest/.
experiment: check-config
	$(MAKE) validate-events
	$(MAKE) prepare-run
	$(MAKE) run-simulation
	$(MAKE) run-resampler-all
	$(MAKE) run-sample-grid
	$(MAKE) calibrate
	$(MAKE) reconstruct-pixel-study
	$(MAKE) benchmark
	$(MAKE) visualize-pixel-study
	@echo "V10 experiment completed. Results are under runs/latest/."

run-visualization: visualize-pixel-study

EIID_Recon_V10: reconstruction
grid_resampler: resampler
geant4_simulator: simulation
eiid_translator: translator
eiid_plotter: visualization
doppler_sample_generator: sample-generator
response_calibrator: response-calibration

v10-all: check-config common pixel-integration simulation-support \
	response-kernel reconstruction resampler simulation translator visualization \
	sample-generator response-calibration kernel-benchmark

test: check-config
	$(MAKE) -C common test
	$(MAKE) -C PixelIntegration test
	$(MAKE) -C SimulationSupport test
	$(MAKE) -C ResponseKernel test
	$(MAKE) -C Reconstruction test
	$(MAKE) -C Geant4_Simulation test

clean:
	@for module in $(MODULES); do \
		$(MAKE) -C $$module clean || exit $$?; \
	done

help:
	@echo "First use"
	@echo "  make configure        Discover dependencies once."
	@echo "  make all              Build every V10 module."
	@echo "  make test             Run unit tests, including child-pixel mapping."
	@echo "Complete experiment"
	@echo "  Place external events.root in the V10 root, then run:"
	@echo "  make experiment       Run efficiency, calibration and pixel study."
	@echo "Individual stages"
	@echo "  make run-simulation / run-resampler-all / run-sample-grid / calibrate"
	@echo "  make reconstruct-pixel-study / benchmark / visualize-pixel-study"
	@echo "Individual reconstructions"
	@echo "  make reconstruct-center / reconstruct-integrated-16"
	@echo "  make reconstruct-integrated-32 / reconstruct-iteration-20"

.PHONY: all configure check-config show-config common pixel-integration \
	simulation-support response-kernel reconstruction resampler simulation \
	translator visualization sample-generator response-calibration \
	kernel-benchmark validate-events prepare-run run-simulation run-resampler \
	run-resampler-all run-sample-grid calibrate check-response-ready \
	reconstruct-center reconstruct-integrated-16 reconstruct-integrated-32 \
	reconstruct-iteration-20 reconstruct-default reconstruct-pixel-study \
	benchmark visualize-center visualize-integrated-16 visualize-integrated-32 \
	visualize-iteration-20 visualize-pixel-study experiment run-visualization \
	EIID_Recon_V10 grid_resampler geant4_simulator eiid_translator eiid_plotter \
	doppler_sample_generator response_calibrator v10-all test clean help
