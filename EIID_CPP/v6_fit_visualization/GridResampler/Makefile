EIID_LOCAL_CONFIG ?= ../config/local.mk
-include $(EIID_LOCAL_CONFIG)

CXX ?= g++
PKG_CONFIG ?= pkg-config
ROOT_CONFIG ?= root-config
PROJECT_CXX_STANDARD ?= c++20

TARGET := grid_resampler
COMMON_DIR := ../common
COMMON_LIBRARY := $(COMMON_DIR)/libeiid_common.a
SOURCES := $(wildcard src/*.cpp)
OBJECTS := $(SOURCES:.cpp=.o)

ROOT_CFLAGS_RAW ?= $(shell $(ROOT_CONFIG) --cflags 2>/dev/null)
ROOT_CFLAGS := $(filter-out -std=%,$(ROOT_CFLAGS_RAW))
ROOT_LIBS ?= $(shell $(ROOT_CONFIG) --glibs 2>/dev/null)
HEALPIX_CFLAGS ?= $(shell $(PKG_CONFIG) --cflags healpix_cxx 2>/dev/null)
HEALPIX_LIBS ?= $(shell $(PKG_CONFIG) --libs healpix_cxx 2>/dev/null)
JSON_CFLAGS ?= $(shell $(PKG_CONFIG) --cflags nlohmann_json 2>/dev/null)

CXXFLAGS := -O2 -Wall -Wextra -pedantic \
	-Iinclude -I$(COMMON_DIR)/include \
	$(ROOT_CFLAGS) $(HEALPIX_CFLAGS) $(JSON_CFLAGS) \
	-std=$(PROJECT_CXX_STANDARD)

all: check-config $(TARGET)

check-config:
	@if test "$(EIID_LOCAL_CONFIGURED)" != "1"; then \
		echo "Error: missing $(EIID_LOCAL_CONFIG)."; \
		echo "Run 'make configure' from the V6 root once."; \
		exit 1; \
	fi

common-library:
	$(MAKE) -C $(COMMON_DIR)

$(TARGET): $(OBJECTS) common-library
	$(CXX) $(OBJECTS) $(COMMON_LIBRARY) -o $@ $(ROOT_LIBS) $(HEALPIX_LIBS) $(EIID_RPATH_FLAGS)

src/%.o: src/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(OBJECTS): | check-config

clean:
	rm -f $(OBJECTS) $(TARGET)

.PHONY: all check-config common-library clean
