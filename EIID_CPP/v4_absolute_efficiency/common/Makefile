EIID_LOCAL_CONFIG ?= ../config/local.mk
-include $(EIID_LOCAL_CONFIG)

CXX ?= g++
AR ?= ar
PKG_CONFIG ?= pkg-config
PROJECT_CXX_STANDARD ?= c++20

TARGET := libeiid_common.a
TEST_TARGET := tests/test_absolute_efficiency
SOURCES := src/HealpixGrid.cpp src/AbsoluteEfficiencyMap.cpp
OBJECTS := $(SOURCES:.cpp=.o)

HEALPIX_CFLAGS ?= $(shell $(PKG_CONFIG) --cflags healpix_cxx 2>/dev/null)

CXXFLAGS := -O2 -Wall -Wextra -pedantic -Iinclude $(HEALPIX_CFLAGS) \
	-std=$(PROJECT_CXX_STANDARD)

all: check-config $(TARGET)

check-config:
	@if test "$(EIID_LOCAL_CONFIGURED)" != "1"; then \
		echo "Error: missing $(EIID_LOCAL_CONFIG)."; \
		echo "Run 'make configure' from the V4 root once."; \
		exit 1; \
	fi

$(TARGET): $(OBJECTS)
	$(AR) rcs $@ $^

src/%.o: src/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(OBJECTS): | check-config

clean:
	rm -f $(OBJECTS) $(TARGET) $(TEST_TARGET) $(TEST_TARGET).exe

test: $(TEST_TARGET)
	./$(TEST_TARGET)

$(TEST_TARGET): src/AbsoluteEfficiencyMap.cpp tests/test_absolute_efficiency.cpp
	$(CXX) -Wall -Wextra -pedantic -Iinclude $^ -o $@ \
		-std=$(PROJECT_CXX_STANDARD)

.PHONY: all check-config test clean
