#include "GaussianLorentzianMixtureKernel.h"

#include <cassert>
#include <cmath>

namespace
{
KernelParameterTable makeTable()
{
    KernelParameters parameters;
    parameters.energyMeV = 0.662;
    parameters.scatterAngleDegree = 45.0;
    parameters.voigtMeanDegree = 0.0;
    parameters.voigtGaussianSigmaDegree = 1.0;
    parameters.voigtLorentzFwhmDegree = 1.0;
    parameters.doubleGaussianMeanDegree = 0.0;
    parameters.doubleGaussianCoreSigmaDegree = 1.0;
    parameters.doubleGaussianTailSigmaDegree = 3.0;
    parameters.doubleGaussianCoreWeight = 0.8;
    parameters.gaussianLorentzianMeanDegree = 0.0;
    parameters.gaussianLorentzianSigmaDegree = 1.2;
    parameters.gaussianLorentzianLorentzFwhmDegree = 2.5;
    parameters.gaussianLorentzianLorentzWeight = 0.25;

    KernelParameterTable table;
    table.add(parameters);
    table.finalize();
    return table;
}
}

int main()
{
    const GaussianLorentzianMixtureKernel kernel{makeTable()};
    constexpr double minimum = -2000.0;
    constexpr double maximum = 2000.0;
    constexpr int bins = 800000;
    const double binWidth = (maximum - minimum) / bins;
    double integral = 0.0;

    for (int bin = 0; bin < bins; ++bin)
    {
        const double arm = minimum + (bin + 0.5) * binWidth;
        integral += kernel.evaluate(ResponseQuery{arm, 0.662, 45.0}) *
            binWidth;
    }

    // The Lorentzian has infinite support. At +/-2000 degrees the omitted
    // probability is below this tolerance for the configured test width.
    assert(std::abs(integral - 1.0) < 3.0e-4);
    assert(kernel.evaluate(ResponseQuery{0.0, 0.662, 45.0}) >
           kernel.evaluate(ResponseQuery{10.0, 0.662, 45.0}));
    return 0;
}
