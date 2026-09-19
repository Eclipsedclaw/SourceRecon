CXX = g++
TARGET = eiid_reconstruction

ROOT_CFLAGS = $(shell root-config --cflags)
ROOT_LIBS = $(shell root-config --glibs)

HEALPIX_CFLAGS = $(shell pkg-config --cflags healpix_cxx 2>/dev/null)
HEALPIX_LIBS = $(shell pkg-config --libs healpix_cxx 2>/dev/null)

# 某些旧 HEALPix 安装没有 pkg-config 文件，此时保留传统链接选项作为后备。
ifeq ($(strip $(HEALPIX_LIBS)),)
HEALPIX_CFLAGS = -I$(CONDA_PREFIX)/include/healpix_cxx
HEALPIX_LIBS = -L$(CONDA_PREFIX)/lib -lhealpix_cxx -lcxxsupport
endif

CXXFLAGS = -std=c++17 -Wall -Wextra -pedantic -O2 -Iinclude $(ROOT_CFLAGS) $(HEALPIX_CFLAGS)
LDLIBS = $(ROOT_LIBS) $(HEALPIX_LIBS)

CORE_SOURCES = $(wildcard core/*.cpp)
IO_SOURCES = $(wildcard io/*.cpp)
SOURCES = main.cpp $(CORE_SOURCES) $(IO_SOURCES)
OBJECTS = $(SOURCES:.cpp=.o)

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CXX) $(OBJECTS) -o $(TARGET) $(LDLIBS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f main.o core/*.o io/*.o $(TARGET)

.PHONY: all clean
