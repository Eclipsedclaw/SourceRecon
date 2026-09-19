#include "DoubleGaussianKernel.h"
#include "FixedGaussianKernel.h"
#include "VoigtKernel.h"

#include <cassert>
#include <cmath>

namespace
{
KernelParameterTable onePointTable()
{
    KernelParameters row;
    row.energyMeV = 0.662;
    row.scatterAngleDegree = 45.0;
    row.voigtMeanDegree = 0.0;
    row.voigtGaussianSigmaDegree = 1.0;
    row.voigtLorentzFwhmDegree = 1.0;
    row.doubleGaussianMeanDegree = 0.0;
    row.doubleGaussianCoreSigmaDegree = 1.0;
    row.doubleGaussianTailSigmaDegree = 4.0;
    row.doubleGaussianCoreWeight = 0.8;

    KernelParameterTable table;
    table.add(row);
    table.finalize();
    return table;
}

template <typename Kernel>
double integrate(const Kernel& kernel, double minimum, double maximum, int bins)
{
    const double width = (maximum - minimum) / static_cast<double>(bins);
    double sum = 0.0;

    for (int index = 0; index < bins; ++index)
    {
        const double x = minimum + (static_cast<double>(index) + 0.5) * width;
        sum += kernel.evaluate(ResponseQuery{x, 0.662, 45.0}) * width;
    }

    return sum;
}
}

int main()
{
    const FixedGaussianKernel fixed{2.0};
    const DoubleGaussianKernel mixture{onePointTable()};
    const VoigtKernel voigt{onePointTable()};

    assert(std::abs(integrate(fixed, -100.0, 100.0, 200000) - 1.0) < 1.0e-5);
    assert(std::abs(integrate(mixture, -100.0, 100.0, 200000) - 1.0) < 1.0e-5);
    assert(std::abs(integrate(voigt, -180.0, 180.0, 360000) - 1.0) < 0.01);
    return 0;
}
