EIID_LOCAL_CONFIG ?= ../config/local.mk
-include $(EIID_LOCAL_CONFIG)

CXX ?= g++
ROOT_CONFIG ?= root-config
GEANT4_CONFIG ?= geant4-config
PROJECT_CXX_STANDARD ?= c++20

SIM_TARGET := doppler_sample_generator
COMPARE_TARGET := doppler_compare
SUPPORT_DIR := ../SimulationSupport
SUPPORT_LIBRARY := $(SUPPORT_DIR)/libsimulation_support.a

SIM_CPP_SOURCES := \
	src/AutoBoundingConePolicy.cpp \
	src/ConfigManager.cpp \
	src/DetectorGeometryInfo.cpp \
	src/ExperimentEventAction.cpp \
	src/ExperimentPhysicsList.cpp \
	src/ExperimentRunAction.cpp \
	src/FixedPointSourceAction.cpp \
	src/main.cpp \
	io/ExperimentRootWriter.cpp
SIM_CC_SOURCES := \
	src/DetectorConstruction.cc \
	src/DetectorMessenger.cc \
	src/TrackerHit.cc \
	src/TrackerSD.cc
SIM_OBJECTS := $(SIM_CPP_SOURCES:.cpp=.o) $(SIM_CC_SOURCES:.cc=.o)
COMPARE_OBJECT := src/compare_results.o

ROOT_CFLAGS_RAW ?= $(shell $(ROOT_CONFIG) --cflags 2>/dev/null)
ROOT_CFLAGS := $(filter-out -std=%,$(ROOT_CFLAGS_RAW))
ROOT_LIBS ?= $(shell $(ROOT_CONFIG) --glibs 2>/dev/null)
GEANT4_CFLAGS_RAW ?= $(shell $(GEANT4_CONFIG) --cflags 2>/dev/null)
GEANT4_CFLAGS := $(filter-out -std=%,$(GEANT4_CFLAGS_RAW))
GEANT4_LIBS ?= $(shell $(GEANT4_CONFIG) --libs 2>/dev/null)

CXXFLAGS := -O2 -Wall -Wextra -pedantic \
	-Iinclude -Iio -I$(SUPPORT_DIR)/include \
	$(JSON_CFLAGS) $(ROOT_CFLAGS) $(GEANT4_CFLAGS) \
	-std=$(PROJECT_CXX_STANDARD)

all: check-config check-geant4 $(SIM_TARGET) $(COMPARE_TARGET)

check-config:
	@if test "$(EIID_LOCAL_CONFIGURED)" != "1"; then \
		echo "Error: dependency configuration is missing."; \
		echo "Run 'make configure' from the V8 root once."; \
		exit 1; \
	fi

check-geant4:
	@if test -z "$(strip $(GEANT4_LIBS))"; then \
		echo "Error: Geant4 was not found by configure.sh."; \
		exit 1; \
	fi

support-library:
	$(MAKE) -C $(SUPPORT_DIR)

$(SIM_TARGET): $(SIM_OBJECTS) support-library
	$(CXX) $(SIM_OBJECTS) $(SUPPORT_LIBRARY) -o $@ $(ROOT_LIBS) $(GEANT4_LIBS) $(EIID_RPATH_FLAGS)

$(COMPARE_TARGET): $(COMPARE_OBJECT)
	$(CXX) $^ -o $@ $(ROOT_LIBS) $(EIID_RPATH_FLAGS)

src/%.o: src/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

src/%.o: src/%.cc
	$(CXX) $(CXXFLAGS) -c $< -o $@

io/%.o: io/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(SIM_OBJECTS) $(COMPARE_OBJECT): | check-config
$(SIM_OBJECTS): | check-geant4

# 每个 run-* 目标都会在同一条 shell 命令内载入与编译版本匹配的
# Geant4 数据集和动态库路径，不依赖用户手工 export。
run-free: check-config check-geant4 $(SIM_TARGET)
	@eval "$$($(GEANT4_CONFIG) --sh)" && ./$(SIM_TARGET) config/free.json

smoke-free: check-config check-geant4 $(SIM_TARGET)
	@eval "$$($(GEANT4_CONFIG) --sh)" && ./$(SIM_TARGET) config/smoke_free.json

run-livermore: check-config check-geant4 $(SIM_TARGET)
	@eval "$$($(GEANT4_CONFIG) --sh)" && ./$(SIM_TARGET) config/livermore.json

run-calibration-grid: check-config check-geant4 $(SIM_TARGET)
	@eval "$$($(GEANT4_CONFIG) --sh)" && ./$(SIM_TARGET) config/livermore_0p300.json
	@eval "$$($(GEANT4_CONFIG) --sh)" && ./$(SIM_TARGET) config/livermore_0p500.json
	@eval "$$($(GEANT4_CONFIG) --sh)" && ./$(SIM_TARGET) config/livermore_0p662.json
	@eval "$$($(GEANT4_CONFIG) --sh)" && ./$(SIM_TARGET) config/livermore_1p000.json
	@eval "$$($(GEANT4_CONFIG) --sh)" && ./$(SIM_TARGET) config/livermore_2p000.json

run-lowep: check-config check-geant4 $(SIM_TARGET)
	@eval "$$($(GEANT4_CONFIG) --sh)" && ./$(SIM_TARGET) config/lowep.json

run-core: run-free run-livermore

run-all-models: run-free run-livermore run-lowep

compare: check-config $(COMPARE_TARGET)
	./$(COMPARE_TARGET) config/comparison.json

# 最便宜、也是最关键的实验默认只跑 free 与 Livermore 两组。
# LowEP 是可选第三组，可先 make run-lowep，再重新 make compare。
experiment: run-core compare

clean:
	rm -f $(SIM_OBJECTS) $(COMPARE_OBJECT) \
		src/ExperimentSteppingAction.o src/PrimaryGammaTrace.o \
		$(SIM_TARGET) $(COMPARE_TARGET)

help:
	@echo "Run 'make configure' once from the V8 project root."
	@echo "make all             - compile simulator and comparison tool"
	@echo "make smoke-free      - run a 10,000-event tracking smoke test"
	@echo "make experiment      - run free + Livermore, then draw comparison"
	@echo "make run-calibration-grid - generate the five V8 calibration energies"
	@echo "make run-lowep       - run optional LowEP model"
	@echo "make compare         - redraw figures from existing ROOT files"

.PHONY: all check-config check-geant4 support-library smoke-free run-free run-livermore run-calibration-grid \
	run-lowep run-core run-all-models compare experiment clean help
