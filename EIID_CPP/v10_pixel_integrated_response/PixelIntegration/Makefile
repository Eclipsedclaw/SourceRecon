EIID_LOCAL_CONFIG ?= ../config/local.mk
-include $(EIID_LOCAL_CONFIG)

CXX ?= g++
PROJECT_CXX_STANDARD ?= c++20

TARGET := libpixel_integration.a
TEST_TARGET := tests/test_pixel_sampling
COMMON_DIR := ../common
SOURCES := $(wildcard src/*.cpp)
OBJECTS := $(SOURCES:.cpp=.o)

CXXFLAGS := -O2 -Wall -Wextra -pedantic \
	-Iinclude -I$(COMMON_DIR)/include $(HEALPIX_CFLAGS) \
	-std=$(PROJECT_CXX_STANDARD)

all: check-config $(TARGET)

check-config:
	@if test "$(EIID_LOCAL_CONFIGURED)" != "1"; then \
		echo "Error: missing $(EIID_LOCAL_CONFIG)."; \
		echo "Run 'make configure' from the V10 root once."; \
		exit 1; \
	fi

$(TARGET): $(OBJECTS)
	ar rcs $@ $^

src/%.o: src/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(OBJECTS): | check-config

test: check-config $(TEST_TARGET)
	./$(TEST_TARGET)

$(TEST_TARGET): $(SOURCES) tests/test_pixel_sampling.cpp
	$(CXX) $(CXXFLAGS) $^ -o $@ $(HEALPIX_LIBS) $(EIID_RPATH_FLAGS)

clean:
	rm -f $(OBJECTS) $(TARGET) $(TEST_TARGET) $(TEST_TARGET).exe

.PHONY: all check-config test clean
