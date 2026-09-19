EIID_LOCAL_CONFIG ?= ../config/local.mk
-include $(EIID_LOCAL_CONFIG)

CXX ?= g++
PROJECT_CXX_STANDARD ?= c++20

TARGET := libsimulation_support.a
OBJECTS := src/CalibrationSchema.o
TEST_TARGET := tests/test_calibration_schema
CXXFLAGS := -O2 -Wall -Wextra -pedantic -Iinclude -std=$(PROJECT_CXX_STANDARD)

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

$(TEST_TARGET): tests/test_calibration_schema.cpp $(TARGET)
	$(CXX) $(CXXFLAGS) $< $(TARGET) -o $@

test: check-config $(TEST_TARGET)
	./$(TEST_TARGET)

clean:
	rm -f $(OBJECTS) $(TARGET) $(TEST_TARGET) $(TEST_TARGET).exe

.PHONY: all check-config test clean
