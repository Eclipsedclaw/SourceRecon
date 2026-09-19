CXX = g++
CXXFLAGS = -std=c++17 -Wall -Wextra -pedantic -O2
TARGET = eiid_core
SOURCES = main.cpp parameter.cpp grid.cpp eiid.cpp

all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CXX) $(CXXFLAGS) $(SOURCES) -o $(TARGET)

clean:
	rm -f $(TARGET)

.PHONY: all clean
