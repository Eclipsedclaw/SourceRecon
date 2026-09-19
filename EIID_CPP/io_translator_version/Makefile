# D:\CodexForSR\EIID_CPP\io_translator_version\Makefile

CXX = g++

TRANSLATOR_TARGET = eiid_translator
RECONSTRUCTION_TARGET = eiid_reconstruction

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

TRANSLATOR_OBJECTS = translate_main.o io/io_config.o io/root_simulation_translator.o

RECONSTRUCTION_OBJECTS = main.o \
	core/parameter.o \
	core/grid.o \
	core/eiid.o \
	io/io_config.o \
	io/data_input.o \
	io/data_output.o

all: $(TRANSLATOR_TARGET) $(RECONSTRUCTION_TARGET)

$(TRANSLATOR_TARGET): $(TRANSLATOR_OBJECTS)
	$(CXX) $(TRANSLATOR_OBJECTS) -o $@ $(ROOT_LIBS)

$(RECONSTRUCTION_TARGET): $(RECONSTRUCTION_OBJECTS)
	$(CXX) $(RECONSTRUCTION_OBJECTS) -o $@ $(ROOT_LIBS) $(HEALPIX_LIBS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f main.o translate_main.o core/*.o io/*.o $(TRANSLATOR_TARGET) $(RECONSTRUCTION_TARGET)

.PHONY: all clean
