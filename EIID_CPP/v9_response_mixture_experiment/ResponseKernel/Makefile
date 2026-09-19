EIID_LOCAL_CONFIG ?= ../config/local.mk
-include $(EIID_LOCAL_CONFIG)

CXX ?= g++
ROOT_CONFIG ?= root-config
PROJECT_CXX_STANDARD ?= c++20

TARGET := libresponse_kernel.a
COMMON_INCLUDE := ../common/include
SOURCES := $(wildcard src/*.cpp) $(wildcard io/*.cpp)
OBJECTS := $(SOURCES:.cpp=.o)
TEST_INTERPOLATION := tests/test_kernel_interpolation
TEST_NORMALIZATION := tests/test_kernel_normalization
TEST_GAUSSIAN_LORENTZIAN := tests/test_gaussian_lorentzian_mixture

ROOT_CFLAGS_RAW ?= $(shell $(ROOT_CONFIG) --cflags 2>/dev/null)
ROOT_CFLAGS := $(filter-out -std=%,$(ROOT_CFLAGS_RAW))
ROOT_LIBS ?= $(shell $(ROOT_CONFIG) --glibs 2>/dev/null)

CXXFLAGS := -O2 -Wall -Wextra -pedantic -Iinclude -I$(COMMON_INCLUDE) \
	$(ROOT_CFLAGS) -std=$(PROJECT_CXX_STANDARD)

all: check-config $(TARGET)

check-config:
	@if test "$(EIID_LOCAL_CONFIGURED)" != "1"; then \
		echo "Error: missing $(EIID_LOCAL_CONFIG)."; \
		echo "Run 'make configure' from the V9 root once."; \
		exit 1; \
	fi

$(TARGET): $(OBJECTS)
	ar rcs $@ $^

src/%.o: src/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

io/%.o: io/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(OBJECTS): | check-config

$(TEST_INTERPOLATION): tests/test_kernel_interpolation.cpp src/KernelParameterTable.cpp
	$(CXX) $(CXXFLAGS) $^ -o $@

$(TEST_NORMALIZATION): tests/test_kernel_normalization.cpp \
	src/KernelParameterTable.cpp src/FixedGaussianKernel.cpp \
	src/DoubleGaussianKernel.cpp src/GaussianLorentzianMixtureKernel.cpp \
	src/VoigtKernel.cpp
	$(CXX) $(CXXFLAGS) $^ -o $@ $(ROOT_LIBS) $(EIID_RPATH_FLAGS)

$(TEST_GAUSSIAN_LORENTZIAN): \
	tests/test_gaussian_lorentzian_mixture.cpp \
	src/KernelParameterTable.cpp \
	src/GaussianLorentzianMixtureKernel.cpp
	$(CXX) $(CXXFLAGS) $^ -o $@

test: check-config $(TEST_INTERPOLATION) $(TEST_NORMALIZATION) \
	$(TEST_GAUSSIAN_LORENTZIAN)
	./$(TEST_INTERPOLATION)
	./$(TEST_NORMALIZATION)
	./$(TEST_GAUSSIAN_LORENTZIAN)

clean:
	rm -f $(OBJECTS) $(TARGET) $(TEST_INTERPOLATION) \
		$(TEST_INTERPOLATION).exe $(TEST_NORMALIZATION) \
		$(TEST_NORMALIZATION).exe $(TEST_GAUSSIAN_LORENTZIAN) \
		$(TEST_GAUSSIAN_LORENTZIAN).exe

.PHONY: all check-config test clean
