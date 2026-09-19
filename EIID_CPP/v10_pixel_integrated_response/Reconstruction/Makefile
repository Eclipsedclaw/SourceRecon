EIID_LOCAL_CONFIG ?= ../config/local.mk
-include $(EIID_LOCAL_CONFIG)

CXX ?= g++
PKG_CONFIG ?= pkg-config
ROOT_CONFIG ?= root-config
PROJECT_CXX_STANDARD ?= c++20

TARGET := EIID_Recon_V10
MLEM_TEST_TARGET := tests/test_efficiency_weighted_mlem
INTEGRATION_TEST_TARGET := tests/test_pixel_integrated_response
TEST_TARGETS := $(MLEM_TEST_TARGET) $(INTEGRATION_TEST_TARGET)
COMMON_DIR := ../common
COMMON_LIBRARY := $(COMMON_DIR)/libeiid_common.a
RESPONSE_DIR := ../ResponseKernel
RESPONSE_LIBRARY := $(RESPONSE_DIR)/libresponse_kernel.a
PIXEL_INTEGRATION_DIR := ../PixelIntegration
PIXEL_INTEGRATION_LIBRARY := $(PIXEL_INTEGRATION_DIR)/libpixel_integration.a
SOURCES := $(wildcard src/*.cpp) $(wildcard io/*.cpp)
OBJECTS := $(SOURCES:.cpp=.o)

ROOT_CFLAGS_RAW ?= $(shell $(ROOT_CONFIG) --cflags 2>/dev/null)
ROOT_CFLAGS := $(filter-out -std=%,$(ROOT_CFLAGS_RAW))
ROOT_LIBS ?= $(shell $(ROOT_CONFIG) --glibs 2>/dev/null)
HEALPIX_CFLAGS ?= $(shell $(PKG_CONFIG) --cflags healpix_cxx 2>/dev/null)
HEALPIX_LIBS ?= $(shell $(PKG_CONFIG) --libs healpix_cxx 2>/dev/null)
JSON_CFLAGS ?= $(shell $(PKG_CONFIG) --cflags nlohmann_json 2>/dev/null)

CXXFLAGS := -O2 -Wall -Wextra -pedantic \
	-Iinclude -I$(COMMON_DIR)/include -I$(RESPONSE_DIR)/include \
	-I$(PIXEL_INTEGRATION_DIR)/include \
	$(ROOT_CFLAGS) $(HEALPIX_CFLAGS) $(JSON_CFLAGS) \
	-std=$(PROJECT_CXX_STANDARD)

all: check-config $(TARGET)

check-config:
	@if test "$(EIID_LOCAL_CONFIGURED)" != "1"; then \
		echo "Error: missing $(EIID_LOCAL_CONFIG)."; \
		echo "Run 'make configure' from the V10 root once."; \
		exit 1; \
	fi

common-library:
	$(MAKE) -C $(COMMON_DIR)

response-library:
	$(MAKE) -C $(RESPONSE_DIR)

pixel-integration-library:
	$(MAKE) -C $(PIXEL_INTEGRATION_DIR)

$(TARGET): $(OBJECTS) common-library response-library pixel-integration-library
	$(CXX) $(OBJECTS) $(RESPONSE_LIBRARY) $(PIXEL_INTEGRATION_LIBRARY) $(COMMON_LIBRARY) -o $@ $(ROOT_LIBS) $(HEALPIX_LIBS) $(EIID_RPATH_FLAGS)

src/%.o: src/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

io/%.o: io/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(OBJECTS): | check-config

clean:
	rm -f $(OBJECTS) $(TARGET) $(TEST_TARGETS) \
		$(addsuffix .exe,$(TEST_TARGETS))

test: check-config $(TEST_TARGETS)
	./$(MLEM_TEST_TARGET)
	./$(INTEGRATION_TEST_TARGET)

$(MLEM_TEST_TARGET): \
	src/LmMlemSolver.cpp \
	src/ReconConfig.cpp \
	../common/src/AbsoluteEfficiencyMap.cpp \
	tests/test_efficiency_weighted_mlem.cpp
	$(CXX) $(CXXFLAGS) $(filter %.cpp,$^) -o $@ $(EIID_RPATH_FLAGS)

$(INTEGRATION_TEST_TARGET): \
	src/EiidResponse.cpp \
	src/PixelIntegratedResponseEvaluator.cpp \
	src/ReconConfig.cpp \
	tests/test_pixel_integrated_response.cpp
	$(CXX) $(CXXFLAGS) $(filter %.cpp,$^) -o $@ $(EIID_RPATH_FLAGS)

.PHONY: all check-config common-library response-library \
	pixel-integration-library test clean
