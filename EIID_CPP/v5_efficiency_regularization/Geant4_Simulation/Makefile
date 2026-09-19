EIID_LOCAL_CONFIG ?= ../config/local.mk
-include $(EIID_LOCAL_CONFIG)

CXX ?= g++
PKG_CONFIG ?= pkg-config
ROOT_CONFIG ?= root-config
GEANT4_CONFIG ?= geant4-config
PROJECT_CXX_STANDARD ?= c++20

TARGET := geant4_simulator
TEST_TARGET := tests/test_absolute_efficiency_estimator
SIM_CONFIG ?= config/sim_config.json
COMMON_INCLUDE := ../common/include
CPP_SOURCES := $(wildcard src/*.cpp) $(wildcard io/*.cpp)
CC_SOURCES := $(wildcard src/*.cc)
OBJECTS := $(CPP_SOURCES:.cpp=.o) $(CC_SOURCES:.cc=.o)

ROOT_CFLAGS_RAW ?= $(shell $(ROOT_CONFIG) --cflags 2>/dev/null)
ROOT_CFLAGS := $(filter-out -std=%,$(ROOT_CFLAGS_RAW))
ROOT_LIBS ?= $(shell $(ROOT_CONFIG) --glibs 2>/dev/null)
HEALPIX_CFLAGS ?= $(shell $(PKG_CONFIG) --cflags healpix_cxx 2>/dev/null)
HEALPIX_LIBS ?= $(shell $(PKG_CONFIG) --libs healpix_cxx 2>/dev/null)
JSON_CFLAGS ?= $(shell $(PKG_CONFIG) --cflags nlohmann_json 2>/dev/null)
GEANT4_CFLAGS_RAW ?= $(shell $(GEANT4_CONFIG) --cflags 2>/dev/null)
GEANT4_CFLAGS := $(filter-out -std=%,$(GEANT4_CFLAGS_RAW))
GEANT4_LIBS ?= $(shell $(GEANT4_CONFIG) --libs 2>/dev/null)

CXXFLAGS := -O2 -Wall -Wextra -pedantic \
	-Iinclude -Iio -I$(COMMON_INCLUDE) \
	$(ROOT_CFLAGS) $(HEALPIX_CFLAGS) $(JSON_CFLAGS) $(GEANT4_CFLAGS) \
	-std=$(PROJECT_CXX_STANDARD)

all: check-config check-geant4 $(TARGET)

# geant4-config --sh initializes both the matching shared-library paths and
# every Geant4 dataset variable in this recipe's private shell.  It therefore
# works from a fresh terminal without changing the user's global environment.
run: all
	@eval "$$($(GEANT4_CONFIG) --sh)" && ./$(TARGET) "$(SIM_CONFIG)"

check-config:
	@if test "$(EIID_LOCAL_CONFIGURED)" != "1"; then \
		echo "Error: missing $(EIID_LOCAL_CONFIG)."; \
		echo "Run 'make configure' from the V5 root once."; \
		exit 1; \
	fi

check-geant4:
	@if test "$(EIID_HAVE_GEANT4)" != "1" || test -z "$(strip $(GEANT4_LIBS))"; then \
		echo "Error: geant4-config was not found by configure.sh."; \
		echo "Set GEANT4_CONFIG=/absolute/path/to/geant4-config and rerun 'make configure'."; \
		exit 1; \
	fi

$(TARGET): $(OBJECTS)
	$(CXX) $^ -o $@ $(ROOT_LIBS) $(HEALPIX_LIBS) $(GEANT4_LIBS) $(EIID_RPATH_FLAGS)

src/%.o: src/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

src/%.o: src/%.cc
	$(CXX) $(CXXFLAGS) -c $< -o $@

io/%.o: io/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(OBJECTS): | check-config check-geant4

clean:
	rm -f $(OBJECTS) $(TARGET) $(TEST_TARGET) $(TEST_TARGET).exe

test: $(TEST_TARGET)
	./$(TEST_TARGET)

$(TEST_TARGET): src/AbsoluteEfficiencyEstimator.cpp tests/test_absolute_efficiency_estimator.cpp
	$(CXX) -Wall -Wextra -pedantic -Iinclude $^ -o $@ \
		-std=$(PROJECT_CXX_STANDARD)

.PHONY: all run check-config check-geant4 test clean
