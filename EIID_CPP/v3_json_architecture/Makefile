CXX ?= g++
AR ?= ar
PKG_CONFIG ?= pkg-config
ROOT_CONFIG ?= root-config
GEANT4_CONFIG ?= geant4-config

V3_RECONSTRUCTION_TARGET := EIID_Recon_V3
GRID_RESAMPLER_TARGET := grid_resampler
GRID_RESAMPLER_LIBRARY := libgrid_resampler.a
GEANT4_SIMULATION_TARGET := geant4_simulator
PLOTTER_TARGET := eiid_plotter
TRANSLATOR_TARGET := eiid_translator

ROOT_CFLAGS := $(shell $(ROOT_CONFIG) --cflags 2>/dev/null)
ROOT_LIBS := $(shell $(ROOT_CONFIG) --glibs 2>/dev/null)
HEALPIX_CFLAGS := $(shell $(PKG_CONFIG) --cflags healpix_cxx 2>/dev/null)
HEALPIX_LIBS := $(shell $(PKG_CONFIG) --libs healpix_cxx 2>/dev/null)

# 某些旧 HEALPix 安装没有 pkg-config 文件，此时使用 Conda 环境作后备。
ifeq ($(strip $(HEALPIX_LIBS)),)
HEALPIX_CFLAGS = -I$(CONDA_PREFIX)/include/healpix_cxx
HEALPIX_LIBS = -L$(CONDA_PREFIX)/lib -lhealpix_cxx -lcxxsupport
endif

JSON_CFLAGS := $(shell $(PKG_CONFIG) --cflags nlohmann_json 2>/dev/null)
ifeq ($(strip $(JSON_CFLAGS)),)
JSON_CFLAGS = -I$(CONDA_PREFIX)/include
endif

GEANT4_CFLAGS := $(shell $(GEANT4_CONFIG) --cflags 2>/dev/null)
GEANT4_LIBS := $(shell $(GEANT4_CONFIG) --libs 2>/dev/null)

COMMON_CXXFLAGS := -std=c++17 -O2 -Wall -Wextra -pedantic
RECON_CXXFLAGS := $(COMMON_CXXFLAGS) -Iinclude \
	$(ROOT_CFLAGS) $(HEALPIX_CFLAGS) $(JSON_CFLAGS)
RESAMPLER_CXXFLAGS := $(COMMON_CXXFLAGS) -Iinclude -IGridResampler/include \
	$(ROOT_CFLAGS) $(HEALPIX_CFLAGS) $(JSON_CFLAGS)
GEANT4_CXXFLAGS := $(COMMON_CXXFLAGS) \
	-IGeant4_Simulation/include -IGeant4_Simulation/io \
	$(ROOT_CFLAGS) $(HEALPIX_CFLAGS) $(JSON_CFLAGS) $(GEANT4_CFLAGS)
PLOTTER_CXXFLAGS := $(COMMON_CXXFLAGS) -Ivis $(ROOT_CFLAGS) $(JSON_CFLAGS)
TRANSLATOR_CXXFLAGS := $(COMMON_CXXFLAGS) -Iinclude \
	$(ROOT_CFLAGS) $(JSON_CFLAGS)

V3_RECONSTRUCTION_SOURCES := \
	src/main.cpp \
	src/core/ReconConfig.cpp \
	src/core/SensitivityMatrix.cpp \
	src/core/grid.cpp \
	src/core/eiid_core.cpp \
	src/core/mlem_core.cpp \
	src/io/data_input.cpp \
	src/io/data_output.cpp \
	src/io/sensitivity_reader.cpp
V3_RECONSTRUCTION_OBJECTS := $(V3_RECONSTRUCTION_SOURCES:.cpp=.o)

GRID_RESAMPLER_LIBRARY_OBJECTS := \
	GridResampler/src/ResamplerConfig.o \
	GridResampler/src/GridAdapter.o \
	GridResampler/src/ResamplerIO.o \
	GridResampler/src/shared_grid.o \
	GridResampler/src/shared_sensitivity_matrix.o

GEANT4_SIMULATION_CPP_SOURCES := $(wildcard Geant4_Simulation/src/*.cpp) \
	$(wildcard Geant4_Simulation/io/*.cpp)
GEANT4_SIMULATION_CC_SOURCES := $(wildcard Geant4_Simulation/src/*.cc)
GEANT4_SIMULATION_OBJECTS := \
	$(GEANT4_SIMULATION_CPP_SOURCES:.cpp=.o) \
	$(GEANT4_SIMULATION_CC_SOURCES:.cc=.o)

PLOTTER_SOURCES := \
	vis/vis_main.cpp \
	vis/vis_config.cpp \
	vis/reconstruction_data.cpp \
	vis/plot_utils.cpp \
	vis/skymap_plotter.cpp \
	vis/spectrum_plotter.cpp \
	vis/containment_plotter.cpp
PLOTTER_OBJECTS := $(PLOTTER_SOURCES:.cpp=.o)

TRANSLATOR_SOURCES := \
	translate_main.cpp \
	io/io_config.cpp \
	io/root_simulation_translator.cpp
TRANSLATOR_OBJECTS := $(TRANSLATOR_SOURCES:.cpp=.o)

all: v3-all

$(V3_RECONSTRUCTION_TARGET): $(V3_RECONSTRUCTION_OBJECTS)
	$(CXX) $^ -o $@ $(ROOT_LIBS) $(HEALPIX_LIBS)

$(GRID_RESAMPLER_LIBRARY): $(GRID_RESAMPLER_LIBRARY_OBJECTS)
	$(AR) rcs $@ $^

$(GRID_RESAMPLER_TARGET): GridResampler/src/resampler_main.o $(GRID_RESAMPLER_LIBRARY)
	$(CXX) $^ -o $@ $(ROOT_LIBS) $(HEALPIX_LIBS)

$(GEANT4_SIMULATION_TARGET): $(GEANT4_SIMULATION_OBJECTS)
	@if test -z "$(strip $(GEANT4_LIBS))"; then \
		echo "Error: geant4-config was not found. Source the Geant4 environment first."; \
		exit 1; \
	fi
	$(CXX) $^ -o $@ $(ROOT_LIBS) $(HEALPIX_LIBS) $(GEANT4_LIBS)

$(PLOTTER_TARGET): $(PLOTTER_OBJECTS)
	$(CXX) $^ -o $@ $(ROOT_LIBS)

$(TRANSLATOR_TARGET): $(TRANSLATOR_OBJECTS)
	$(CXX) $^ -o $@ $(ROOT_LIBS)

src/%.o: src/%.cpp
	$(CXX) $(RECON_CXXFLAGS) -c $< -o $@

GridResampler/src/%.o: GridResampler/src/%.cpp
	$(CXX) $(RESAMPLER_CXXFLAGS) -c $< -o $@

# 共享对象使用独立文件名，避免与重建器的编译选项互相覆盖。
GridResampler/src/shared_grid.o: src/core/grid.cpp
	$(CXX) $(RESAMPLER_CXXFLAGS) -c $< -o $@

GridResampler/src/shared_sensitivity_matrix.o: src/core/SensitivityMatrix.cpp
	$(CXX) $(RESAMPLER_CXXFLAGS) -c $< -o $@

Geant4_Simulation/src/%.o: Geant4_Simulation/src/%.cpp
	$(CXX) $(GEANT4_CXXFLAGS) -c $< -o $@

Geant4_Simulation/src/%.o: Geant4_Simulation/src/%.cc
	$(CXX) $(GEANT4_CXXFLAGS) -c $< -o $@

Geant4_Simulation/io/%.o: Geant4_Simulation/io/%.cpp
	$(CXX) $(GEANT4_CXXFLAGS) -c $< -o $@

vis/%.o: vis/%.cpp
	$(CXX) $(PLOTTER_CXXFLAGS) -c $< -o $@

translate_main.o: translate_main.cpp
	$(CXX) $(TRANSLATOR_CXXFLAGS) -c $< -o $@

io/io_config.o: io/io_config.cpp
	$(CXX) $(TRANSLATOR_CXXFLAGS) -c $< -o $@

io/root_simulation_translator.o: io/root_simulation_translator.cpp
	$(CXX) $(TRANSLATOR_CXXFLAGS) -c $< -o $@

v3-all: \
	$(V3_RECONSTRUCTION_TARGET) \
	$(GRID_RESAMPLER_TARGET) \
	$(GEANT4_SIMULATION_TARGET) \
	$(PLOTTER_TARGET) \
	$(TRANSLATOR_TARGET)

help:
	@echo "make EIID_Recon_V3    Build the JSON-driven reconstruction engine."
	@echo "make grid_resampler   Build the independent sensitivity-grid adapter."
	@echo "make libgrid_resampler.a Build the adapter as a reusable static library."
	@echo "make geant4_simulator Build the dual-mode Geant4 simulator."
	@echo "make eiid_plotter     Build the independent ROOT visualization module."
	@echo "make eiid_translator  Build the retained raw-Step translator."
	@echo "make v3-all           Build all V3 executables plus the plotter."
	@echo "make clean            Remove generated objects and executables."

clean:
	rm -f \
		src/*.o src/core/*.o src/io/*.o \
		GridResampler/src/*.o \
		Geant4_Simulation/src/*.o Geant4_Simulation/io/*.o \
		vis/*.o io/*.o translate_main.o \
		$(V3_RECONSTRUCTION_TARGET) \
		$(GRID_RESAMPLER_TARGET) \
		$(GRID_RESAMPLER_LIBRARY) \
		$(GEANT4_SIMULATION_TARGET) \
		$(PLOTTER_TARGET) \
		$(TRANSLATOR_TARGET)

.PHONY: all v3-all help clean
