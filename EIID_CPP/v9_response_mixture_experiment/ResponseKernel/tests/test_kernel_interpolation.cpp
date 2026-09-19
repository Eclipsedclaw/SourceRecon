#include "KernelParameterTable.h"

#include <cassert>
#include <cmath>

namespace
{
KernelParameters point(double energy, double angle, double value)
{
    KernelParameters row;
    row.energyMeV = energy;
    row.scatterAngleDegree = angle;
    row.voigtMeanDegree = value;
    row.voigtGaussianSigmaDegree = 1.0 + value;
    row.voigtLorentzFwhmDegree = 0.5 + value;
    row.doubleGaussianMeanDegree = value;
    row.doubleGaussianCoreSigmaDegree = 1.0 + value;
    row.doubleGaussianTailSigmaDegree = 2.0 + value;
    row.doubleGaussianCoreWeight = 0.8;
    row.gaussianLorentzianMeanDegree = value;
    row.gaussianLorentzianSigmaDegree = 1.0 + value;
    row.gaussianLorentzianLorentzFwhmDegree = 2.0 + value;
    row.gaussianLorentzianLorentzWeight = 0.2;
    return row;
}
}

int main()
{
    KernelParameterTable table;
    table.add(point(0.5, 20.0, 0.0));
    table.add(point(1.5, 20.0, 2.0));
    table.add(point(0.5, 60.0, 4.0));
    table.add(point(1.5, 60.0, 6.0));
    table.finalize();

    const KernelParameters middle = table.interpolate(1.0, 40.0);
    assert(std::abs(middle.voigtMeanDegree - 3.0) < 1.0e-12);
    assert(std::abs(middle.doubleGaussianCoreSigmaDegree - 4.0) < 1.0e-12);
    assert(std::abs(middle.gaussianLorentzianMeanDegree - 3.0) < 1.0e-12);

    // Queries outside the calibrated domain clamp to the nearest boundary.
    const KernelParameters edge = table.interpolate(0.1, 100.0);
    assert(std::abs(edge.voigtMeanDegree - 4.0) < 1.0e-12);
    return 0;
}
