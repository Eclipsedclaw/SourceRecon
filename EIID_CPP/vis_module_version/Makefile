# D:\CodexForSR\EIID_CPP\io_translator_version\Makefile

CXX = g++

TRANSLATOR_TARGET = eiid_translator
RECONSTRUCTION_TARGET = eiid_reconstruction
PLOTTER_TARGET = eiid_plotter

ROOT_CFLAGS = $(shell root-config --cflags)
ROOT_LIBS = $(shell root-config --glibs)

HEALPIX_CFLAGS = $(shell pkg-config --cflags healpix_cxx 2>/dev/null)
HEALPIX_LIBS = $(shell pkg-config --libs healpix_cxx 2>/dev/null)

JSON_CFLAGS = $(shell pkg-config --cflags nlohmann_json 2>/dev/null)

# 某些旧 HEALPix 安装没有 pkg-config 文件，此时保留传统链接选项作为后备。
ifeq ($(strip $(HEALPIX_LIBS)),)
HEALPIX_CFLAGS = -I$(CONDA_PREFIX)/include/healpix_cxx
HEALPIX_LIBS = -L$(CONDA_PREFIX)/lib -lhealpix_cxx -lcxxsupport
endif

# nlohmann/json 是单头文件库，不需要链接；Conda 安装通常位于该 include 目录。
ifeq ($(strip $(JSON_CFLAGS)),)
JSON_CFLAGS = -I$(CONDA_PREFIX)/include
endif

COMMON_CXXFLAGS = -std=c++17 -Wall -Wextra -pedantic -O2
CXXFLAGS = $(COMMON_CXXFLAGS) -Iinclude $(ROOT_CFLAGS) $(HEALPIX_CFLAGS)
PLOTTER_CXXFLAGS = $(COMMON_CXXFLAGS) -Ivis $(ROOT_CFLAGS) $(JSON_CFLAGS)

TRANSLATOR_OBJECTS = translate_main.o io/io_config.o io/root_simulation_translator.o

RECONSTRUCTION_OBJECTS = main.o \
	core/parameter.o \
	core/grid.o \
	core/eiid.o \
	io/io_config.o \
	io/data_input.o \
	io/data_output.o

PLOTTER_OBJECTS = vis/vis_main.o \
	vis/vis_config.o \
	vis/reconstruction_data.o \
	vis/plot_utils.o \
	vis/skymap_plotter.o \
	vis/spectrum_plotter.o \
	vis/containment_plotter.o

all: $(TRANSLATOR_TARGET) $(RECONSTRUCTION_TARGET) $(PLOTTER_TARGET)

$(TRANSLATOR_TARGET): $(TRANSLATOR_OBJECTS)
	$(CXX) $(TRANSLATOR_OBJECTS) -o $@ $(ROOT_LIBS)

$(RECONSTRUCTION_TARGET): $(RECONSTRUCTION_OBJECTS)
	$(CXX) $(RECONSTRUCTION_OBJECTS) -o $@ $(ROOT_LIBS) $(HEALPIX_LIBS)

# 绘图器只链接 vis 模块和 ROOT，不依赖 core、Translator 或 HEALPix 算法对象。
$(PLOTTER_TARGET): $(PLOTTER_OBJECTS)
	$(CXX) $(PLOTTER_OBJECTS) -o $@ $(ROOT_LIBS)

# vis 源文件使用自己的编译参数，不继承 HEALPix 或 core 的头文件路径。
vis/%.o: vis/%.cpp
	$(CXX) $(PLOTTER_CXXFLAGS) -c $< -o $@

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f main.o translate_main.o core/*.o io/*.o vis/*.o $(TRANSLATOR_TARGET) $(RECONSTRUCTION_TARGET) $(PLOTTER_TARGET)

clean_1:
	rm -f main.o translate_main.o core/*.o io/*.o vis/*.o

.PHONY: all clean
