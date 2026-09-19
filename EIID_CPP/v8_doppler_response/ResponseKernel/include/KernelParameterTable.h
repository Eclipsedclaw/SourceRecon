#ifndef EIID_V8_KERNEL_PARAMETER_TABLE_H
#define EIID_V8_KERNEL_PARAMETER_TABLE_H

#include "Common.h"

#include <cstddef>
#include <vector>

// One calibration point contains both candidate parameterizations.  A single
// ROOT row can therefore be used by Voigt and double-Gaussian reconstructions,
// guaranteeing that both models use the same energy/angle binning.
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
