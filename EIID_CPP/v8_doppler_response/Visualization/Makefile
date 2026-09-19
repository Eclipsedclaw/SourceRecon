EIID_LOCAL_CONFIG ?= ../config/local.mk
-include $(EIID_LOCAL_CONFIG)

CXX ?= g++
PKG_CONFIG ?= pkg-config
ROOT_CONFIG ?= root-config
PROJECT_CXX_STANDARD ?= c++20

TARGET := eiid_plotter
PLOT_CONFIG ?= config/plot_config.json
SOURCES := $(wildcard src/*.cpp)
OBJECTS := $(SOURCES:.cpp=.o)
ROOT_CFLAGS_RAW ?= $(shell $(ROOT_CONFIG) --cflags 2>/dev/null)
ROOT_CFLAGS := $(filter-out -std=%,$(ROOT_CFLAGS_RAW))
ROOT_LIBS ?= $(shell $(ROOT_CONFIG) --glibs 2>/dev/null)
JSON_CFLAGS ?= $(shell $(PKG_CONFIG) --cflags nlohmann_json 2>/dev/null)
CXXFLAGS := -O2 -Wall -Wextra -pedantic \
	-Iinclude $(ROOT_CFLAGS) $(JSON_CFLAGS) \
	-std=$(PROJECT_CXX_STANDARD)

all: check-config $(TARGET)

check-config:
	@if test "$(EIID_LOCAL_CONFIGURED)" != "1"; then \
		echo "Error: missing $(EIID_LOCAL_CONFIG)."; \
		echo "Run 'make configure' from the V8 root once."; \
		exit 1; \
	fi

$(TARGET): $(OBJECTS)
	$(CXX) $^ -o $@ $(ROOT_LIBS) $(EIID_RPATH_FLAGS)

src/%.o: src/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(OBJECTS): | check-config

clean:
	rm -f $(OBJECTS) $(TARGET)

run: all
	./$(TARGET) $(PLOT_CONFIG)

.PHONY: all check-config clean run
