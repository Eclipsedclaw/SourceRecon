CXX = g++

# 1. 关键修改：加上 -I$(CONDA_PREFIX)/include，告诉编译器去 Conda 的私有目录找 .h 头文件
CXXFLAGS = -std=c++17 -Wall -Wextra -pedantic -O2 -I$(CONDA_PREFIX)/include/healpix_cxx

# 2. 关键修改：加上 -L 指明库文件所在目录，并用 -l 链接 healpix_cxx
LIBS = -L$(CONDA_PREFIX)/lib -lhealpix_cxx -lcxxsupport

TARGET = eiid_core_healpix
SOURCES = main.cpp parameter.cpp grid.cpp eiid.cpp

all: $(TARGET)

$(TARGET): $(SOURCES)
	$(CXX) $(CXXFLAGS) $(SOURCES) -o $(TARGET) $(LIBS)

clean:
	rm -f $(TARGET)

.PHONY: all clean