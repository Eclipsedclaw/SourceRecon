#ifndef EIID_V10_KERNEL_PARAMETER_TABLE_H
#define EIID_V10_KERNEL_PARAMETER_TABLE_H

#include "Common.h"

#include <cstddef>
#include <vector>

// One calibration point contains all candidate parameterizations. A single
// ROOT row is therefore shared by Voigt, double-Gaussian, and independent
// Gaussian-Lorentzian-mixture reconstructions, guaranteeing identical
// energy/angle binning for the benchmark.
struct KernelParameters
{
    Decimal energyMeV{};
    Decimal scatterAngleDegree{};

    Decimal voigtMeanDegree{};
    Decimal voigtGaussianSigmaDegree{};
    Decimal voigtLorentzFwhmDegree{};

    Decimal doubleGaussianMeanDegree{};
    Decimal doubleGaussianCoreSigmaDegree{};
    Decimal doubleGaussianTailSigmaDegree{};
    Decimal doubleGaussianCoreWeight{};

    Decimal gaussianLorentzianMeanDegree{};
    Decimal gaussianLorentzianSigmaDegree{};
    Decimal gaussianLorentzianLorentzFwhmDegree{};
    Decimal gaussianLorentzianLorentzWeight{};
};

class KernelParameterTable
{
public:
    void add(const KernelParameters& parameters);
    void finalize();

    KernelParameters interpolate(
        Decimal energyMeV,
        Decimal scatterAngleDegree
    ) const;

    bool empty() const noexcept;
    std::size_t energyCount() const noexcept;
    std::size_t angleCount() const noexcept;

private:
    std::size_t flatIndex(
        std::size_t energyIndex,
        std::size_t angleIndex
    ) const;

    std::vector<KernelParameters> pending_;
    std::vector<Decimal> energies_;
    std::vector<Decimal> angles_;
    std::vector<KernelParameters> grid_;
    bool finalized_{};
};

#endif
