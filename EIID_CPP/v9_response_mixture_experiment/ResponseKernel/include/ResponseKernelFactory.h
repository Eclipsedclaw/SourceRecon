#ifndef EIID_V9_RESPONSE_KERNEL_FACTORY_H
#define EIID_V9_RESPONSE_KERNEL_FACTORY_H

#include "Common.h"

#include <filesystem>
#include <memory>
#include <string>

class IResponseKernel;

struct ResponseKernelConfig
{
    std::string type{"fixed_gaussian"};
    std::filesystem::path calibrationFile;
    std::string parameterTree{"ResponseParameters"};
    std::string histogramName{"EmpiricalDetectorArmPdf"};
    Decimal fixedSigmaDegree{static_cast<Decimal>(6.0)};
};

class ResponseKernelFactory
{
public:
    static std::unique_ptr<IResponseKernel> create(
        const ResponseKernelConfig& config
    );
};

#endif
