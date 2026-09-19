EIID_LOCAL_CONFIG ?= config/local.mk
-include $(EIID_LOCAL_CONFIG)

MODULES := common SimulationSupport ResponseKernel Reconstruction GridResampler \
	Geant4_Simulation Translator Visualization DopplerSampleGenerator \
	ResponseCalibration KernelBenchmark

SIM_CONFIG ?= config/sim_config.json
VIS_CONFIG ?= config/plot_config.json
CALIBRATION_CONFIG ?= ResponseCalibration/config/calibration_config.json
VOIGT_RECON_CONFIG ?= Reconstruction/config/recon_voigt.json
DOUBLE_GAUSSIAN_RECON_CONFIG ?= Reconstruction/config/recon_double_gaussian.json
BENCHMARK_CONFIG ?= KernelBenchmark/config/benchmark_config.json

all: v8-all

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

run-simulation: simulation
	$(MAKE) -C Geant4_Simulation run SIM_CONFIG="$(SIM_CONFIG)"

translator: check-config
	$(MAKE) -C Translator

visualization: check-config
	$(MAKE) -C Visualization

run-visualization: visualization
	$(MAKE) -C Visualization run PLOT_CONFIG="$(VIS_CONFIG)"

sample-generator: check-config simulation-support
	$(MAKE) -C DopplerSampleGenerator

run-sample-free: sample-generator
	$(MAKE) -C DopplerSampleGenerator run-free

run-sample-livermore: sample-generator
	$(MAKE) -C DopplerSampleGenerator run-livermore

run-sample-grid: sample-generator
	$(MAKE) -C DopplerSampleGenerator run-calibration-grid

response-calibration: check-config simulation-support
	$(MAKE) -C ResponseCalibration

calibrate: response-calibration
	./ResponseCalibration/response_calibrator $(CALIBRATION_CONFIG)

kernel-benchmark: check-config
	$(MAKE) -C KernelBenchmark

reconstruct-voigt: reconstruction
	./Reconstruction/EIID_Recon_V8 $(VOIGT_RECON_CONFIG)

reconstruct-double-gaussian: reconstruction
	./Reconstruction/EIID_Recon_V8 $(DOUBLE_GAUSSIAN_RECON_CONFIG)

benchmark: kernel-benchmark
	./KernelBenchmark/kernel_benchmark $(BENCHMARK_CONFIG)

# This full comparison deliberately reuses the existing events.root and
# absolute_efficiency.root so both kernels see exactly the same data.
response-study:
	$(MAKE) run-sample-grid
	$(MAKE) calibrate
	$(MAKE) reconstruct-voigt
	$(MAKE) reconstruct-double-gaussian
	$(MAKE) benchmark

EIID_Recon_V8: reconstruction
grid_resampler: resampler
geant4_simulator: simulation
eiid_translator: translator
eiid_plotter: visualization
doppler_sample_generator: sample-generator
response_calibrator: response-calibration

v8-all: check-config common simulation-support response-kernel reconstruction \
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
	@echo "Configuration and builds"
	@echo "  make configure                    Discover dependencies once."
	@echo "  make all                          Build every V8 module."
	@echo "  make test                         Run unit tests."
	@echo "Original production workflow"
	@echo "  make simulation / resampler / reconstruction / visualization"
	@echo "New Doppler-response workflow"
	@echo "  make run-sample-livermore         Generate calibration samples."
	@echo "  make run-sample-grid              Generate five calibration energies."
	@echo "  make calibrate                     Fit both response models."
	@echo "  make reconstruct-voigt            Reconstruct with Voigt."
	@echo "  make reconstruct-double-gaussian  Reconstruct with double Gaussian."
	@echo "  make benchmark                     Compare existing results."
	@echo "  make response-study                Run the complete comparison."

.PHONY: all configure check-config show-config common simulation-support \
	response-kernel reconstruction resampler simulation run-simulation \
	translator visualization run-visualization sample-generator \
	run-sample-free run-sample-livermore run-sample-grid response-calibration calibrate \
	kernel-benchmark reconstruct-voigt reconstruct-double-gaussian benchmark \
	response-study EIID_Recon_V8 grid_resampler geant4_simulator \
	eiid_translator eiid_plotter doppler_sample_generator response_calibrator \
	v8-all test clean help
