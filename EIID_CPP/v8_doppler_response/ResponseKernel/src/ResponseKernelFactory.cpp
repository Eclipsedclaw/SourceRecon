#include "ResponseKernelFactory.h"

#include "DoubleGaussianKernel.h"
#include "FixedGaussianKernel.h"
#include "HistogramKernel.h"
#include "IResponseKernel.h"
#include "RootKernelReader.h"
#include "VoigtKernel.h"

#include <stdexcept>

std::unique_ptr<IResponseKernel> ResponseKernelFactory::create(
    const ResponseKernelConfig& config
)
{
    if (config.type == "fixed_gaussian")
    {
        return std::make_unique<FixedGaussianKernel>(config.fixedSigmaDegree);
    }

    if (config.calibrationFile.empty())
    {
        throw std::runtime_error{
            "A calibration file is required for response kernel type " + config.type
        };
    }

    if (config.type == "voigt")
    {
        return std::make_unique<VoigtKernel>(
            RootKernelReader::readParameterTable(
                config.calibrationFile,
                config.parameterTree.c_str(),
                "voigt_converged"
            )
        );
    }

    if (config.type == "double_gaussian")
    {
        return std::make_unique<DoubleGaussianKernel>(
            RootKernelReader::readParameterTable(
                config.calibrationFile,
                config.parameterTree.c_str(),
                "double_gaussian_converged"
            )
        );
    }

    if (config.type == "histogram")
    {
        return RootKernelReader::readHistogramKernel(
            config.calibrationFile,
            config.histogramName.c_str()
        );
    }

    throw std::runtime_error{"Unknown response kernel type: " + config.type};
}
