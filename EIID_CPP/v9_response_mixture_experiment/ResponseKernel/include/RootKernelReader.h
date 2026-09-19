#ifndef EIID_V9_ROOT_KERNEL_READER_H
#define EIID_V9_ROOT_KERNEL_READER_H

#include "KernelParameterTable.h"

#include <filesystem>
#include <memory>

class HistogramKernel;

class RootKernelReader
{
public:
    static KernelParameterTable readParameterTable(
        const std::filesystem::path& filePath,
        const char* treeName = "ResponseParameters",
        const char* convergenceBranch = nullptr
    );

    static std::unique_ptr<HistogramKernel> readHistogramKernel(
        const std::filesystem::path& filePath,
        const char* histogramName = "EmpiricalDetectorArmPdf"
    );
};

#endif
