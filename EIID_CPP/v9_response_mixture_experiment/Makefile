EIID_LOCAL_CONFIG ?= config/local.mk
-include $(EIID_LOCAL_CONFIG)

MODULES := common SimulationSupport ResponseKernel Reconstruction GridResampler \
	Geant4_Simulation Translator Visualization DopplerSampleGenerator \
	ResponseCalibration KernelBenchmark

SIM_CONFIG ?= config/sim_config.json
RESAMPLER_CONFIG ?= GridResampler/config/resampler_config.json
CALIBRATION_CONFIG ?= ResponseCalibration/config/calibration_config.json
VOIGT_RECON_CONFIG ?= Reconstruction/config/recon_voigt.json
DOUBLE_GAUSSIAN_RECON_CONFIG ?= Reconstruction/config/recon_double_gaussian.json
GAUSSIAN_LORENTZIAN_RECON_CONFIG ?= Reconstruction/config/recon_gaussian_lorentzian_mixture.json
BENCHMARK_CONFIG ?= KernelBenchmark/config/benchmark_config.json
MODEL_STATUS_JSON := runs/latest/calibration/model_status.json

all: v9-all

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

simulation-support: check-config
	$(MAKE) -C SimulationSupport

response-kernel: check-config
	$(MAKE) -C ResponseKernel

reconstruction: check-config common response-kernel
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

# events.root is an external input. This target validates its schema before
# any expensive simulation starts.
validate-events: reconstruction
	./Reconstruction/EIID_Recon_V9 --validate-events-only $(DOUBLE_GAUSSIAN_RECON_CONFIG)

# Existing runs/latest is moved to runs/archive instead of being deleted.
prepare-run:
	bash scripts/prepare_run.sh

run-simulation: simulation
	$(MAKE) -C Geant4_Simulation run SIM_CONFIG="$(SIM_CONFIG)"

run-resampler: resampler
	./GridResampler/grid_resampler $(RESAMPLER_CONFIG)

run-sample-free: sample-generator
	$(MAKE) -C DopplerSampleGenerator run-free

run-sample-livermore: sample-generator
	$(MAKE) -C DopplerSampleGenerator run-livermore

run-sample-grid: sample-generator
	$(MAKE) -C DopplerSampleGenerator run-calibration-grid

calibrate: response-calibration
	./ResponseCalibration/response_calibrator $(CALIBRATION_CONFIG)

reconstruct-voigt: reconstruction
	./Reconstruction/EIID_Recon_V9 $(VOIGT_RECON_CONFIG)

reconstruct-double-gaussian: reconstruction
	./Reconstruction/EIID_Recon_V9 $(DOUBLE_GAUSSIAN_RECON_CONFIG)

reconstruct-gaussian-lorentzian: reconstruction
	./Reconstruction/EIID_Recon_V9 $(GAUSSIAN_LORENTZIAN_RECON_CONFIG)

# A response model is reconstructed only if every required calibration bin
# converged. Exit code 2 means a scientific skip; other failures stop the run.
reconstruct-eligible: response-calibration reconstruction
	@test -f "$(MODEL_STATUS_JSON)" || { \
		echo "Error: missing $(MODEL_STATUS_JSON). Run 'make calibrate' first."; \
		exit 1; \
	}
	@status=0; \
	./ResponseCalibration/response_calibrator --model-usable "$(MODEL_STATUS_JSON)" voigt || status=$$?; \
	if test $$status -eq 0; then \
		$(MAKE) reconstruct-voigt; \
	elif test $$status -ne 2; then \
		exit $$status; \
	fi
	@status=0; \
	./ResponseCalibration/response_calibrator --model-usable "$(MODEL_STATUS_JSON)" double_gaussian || status=$$?; \
	if test $$status -eq 0; then \
		$(MAKE) reconstruct-double-gaussian; \
	elif test $$status -ne 2; then \
		exit $$status; \
	fi
	@status=0; \
	./ResponseCalibration/response_calibrator --model-usable "$(MODEL_STATUS_JSON)" gaussian_lorentzian_mixture || status=$$?; \
	if test $$status -eq 0; then \
		$(MAKE) reconstruct-gaussian-lorentzian; \
	elif test $$status -ne 2; then \
		exit $$status; \
	fi

benchmark: kernel-benchmark
	./KernelBenchmark/kernel_benchmark $(BENCHMARK_CONFIG)

visualize-eligible: response-calibration visualization
	@status=0; \
	./ResponseCalibration/response_calibrator --model-usable "$(MODEL_STATUS_JSON)" voigt || status=$$?; \
	if test $$status -eq 0; then \
		./Visualization/eiid_plotter Visualization/config/plot_voigt.json; \
	elif test $$status -ne 2; then \
		exit $$status; \
	fi
	@status=0; \
	./ResponseCalibration/response_calibrator --model-usable "$(MODEL_STATUS_JSON)" double_gaussian || status=$$?; \
	if test $$status -eq 0; then \
		./Visualization/eiid_plotter Visualization/config/plot_double_gaussian.json; \
	elif test $$status -ne 2; then \
		exit $$status; \
	fi
	@status=0; \
	./ResponseCalibration/response_calibrator --model-usable "$(MODEL_STATUS_JSON)" gaussian_lorentzian_mixture || status=$$?; \
	if test $$status -eq 0; then \
		./Visualization/eiid_plotter Visualization/config/plot_gaussian_lorentzian_mixture.json; \
	elif test $$status -ne 2; then \
		exit $$status; \
	fi

# Full V9 experiment. It never creates or overwrites events.root.
experiment: check-config
	$(MAKE) validate-events
	$(MAKE) prepare-run
	$(MAKE) run-simulation
	$(MAKE) run-resampler
	$(MAKE) run-sample-grid
	$(MAKE) calibrate
	$(MAKE) reconstruct-eligible
	$(MAKE) benchmark
	$(MAKE) visualize-eligible
	@echo "V9 experiment completed. Results are under runs/latest/."

run-visualization: visualize-eligible

EIID_Recon_V9: reconstruction
grid_resampler: resampler
geant4_simulator: simulation
eiid_translator: translator
eiid_plotter: visualization
doppler_sample_generator: sample-generator
response_calibrator: response-calibration

v9-all: check-config common simulation-support response-kernel reconstruction \
	resampler simulation translator visualization sample-generator \
	response-calibration kernel-benchmark

test: check-config
	$(MAKE) -C common test
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
	@echo "  make configure       Discover dependencies once."
	@echo "  make all             Build every V9 module."
	@echo "  make test            Run unit tests."
	@echo "Complete experiment"
	@echo "  Place external events.root in the V9 root, then run:"
	@echo "  make experiment      Run the complete model-comparison experiment."
	@echo "Individual stages"
	@echo "  make validate-events / run-simulation / run-resampler / run-sample-grid"
	@echo "  make calibrate / reconstruct-eligible / benchmark / visualize-eligible"

.PHONY: all configure check-config show-config common simulation-support \
	response-kernel reconstruction resampler simulation translator visualization \
	sample-generator response-calibration kernel-benchmark validate-events \
	prepare-run run-simulation run-resampler run-sample-free run-sample-livermore \
	run-sample-grid calibrate reconstruct-voigt reconstruct-double-gaussian \
	reconstruct-gaussian-lorentzian reconstruct-eligible benchmark \
	visualize-eligible experiment run-visualization EIID_Recon_V9 grid_resampler \
	geant4_simulator eiid_translator eiid_plotter doppler_sample_generator \
	response_calibrator v9-all test clean help
