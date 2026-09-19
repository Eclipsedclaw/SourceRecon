#include "RootKernelReader.h"

#include "HistogramKernel.h"

#include "TFile.h"
#include "TH3D.h"
#include "TTree.h"

#include <memory>
#include <stdexcept>
#include <utility>
#include <string>
#include <vector>

namespace
{
void requireBranch(TTree& tree, const char* name)
{
    if (tree.GetBranch(name) == nullptr)
    {
        throw std::runtime_error{"Missing response branch: " + std::string{name}};
    }
}
}

KernelParameterTable RootKernelReader::readParameterTable(
    const std::filesystem::path& filePath,
    const char* treeName,
    const char* convergenceBranch
)
{
    std::unique_ptr<TFile> file{TFile::Open(filePath.string().c_str(), "READ")};

    if (!file || file->IsZombie())
    {
        throw std::runtime_error{"Cannot open response calibration: " + filePath.string()};
    }

    TTree* tree = file->Get<TTree>(treeName);

    if (tree == nullptr)
    {
        throw std::runtime_error{"Cannot find response parameter tree: " + std::string{treeName}};
    }

    const char* branches[] = {
        "energy_MeV", "scatter_angle_degree",
        "voigt_mean_degree", "voigt_gaussian_sigma_degree",
        "voigt_lorentz_fwhm_degree", "double_gaussian_mean_degree",
        "double_gaussian_core_sigma_degree",
        "double_gaussian_tail_sigma_degree",
        "double_gaussian_core_weight",
        "gaussian_lorentzian_mean_degree",
        "gaussian_lorentzian_sigma_degree",
        "gaussian_lorentzian_lorentz_fwhm_degree",
        "gaussian_lorentzian_lorentz_weight"
    };

    for (const char* branch : branches)
    {
        requireBranch(*tree, branch);
    }

    if (convergenceBranch != nullptr)
    {
        requireBranch(*tree, convergenceBranch);
    }

    KernelParameters row;
    Bool_t converged{kTRUE};
    tree->SetBranchAddress("energy_MeV", &row.energyMeV);
    tree->SetBranchAddress("scatter_angle_degree", &row.scatterAngleDegree);
    tree->SetBranchAddress("voigt_mean_degree", &row.voigtMeanDegree);
    tree->SetBranchAddress(
        "voigt_gaussian_sigma_degree",
        &row.voigtGaussianSigmaDegree
    );
    tree->SetBranchAddress(
        "voigt_lorentz_fwhm_degree",
        &row.voigtLorentzFwhmDegree
    );
    tree->SetBranchAddress(
        "double_gaussian_mean_degree",
        &row.doubleGaussianMeanDegree
    );
    tree->SetBranchAddress(
        "double_gaussian_core_sigma_degree",
        &row.doubleGaussianCoreSigmaDegree
    );
    tree->SetBranchAddress(
        "double_gaussian_tail_sigma_degree",
        &row.doubleGaussianTailSigmaDegree
    );
    tree->SetBranchAddress(
        "double_gaussian_core_weight",
        &row.doubleGaussianCoreWeight
    );
    tree->SetBranchAddress(
        "gaussian_lorentzian_mean_degree",
        &row.gaussianLorentzianMeanDegree
    );
    tree->SetBranchAddress(
        "gaussian_lorentzian_sigma_degree",
        &row.gaussianLorentzianSigmaDegree
    );
    tree->SetBranchAddress(
        "gaussian_lorentzian_lorentz_fwhm_degree",
        &row.gaussianLorentzianLorentzFwhmDegree
    );
    tree->SetBranchAddress(
        "gaussian_lorentzian_lorentz_weight",
        &row.gaussianLorentzianLorentzWeight
    );

    if (convergenceBranch != nullptr)
    {
        tree->SetBranchAddress(convergenceBranch, &converged);
    }

    KernelParameterTable table;

    for (Long64_t entry = 0; entry < tree->GetEntries(); ++entry)
    {
        tree->GetEntry(entry);

        if (convergenceBranch != nullptr && converged == kFALSE)
        {
            throw std::runtime_error{
                "Response fit did not converge in entry " +
                std::to_string(entry) + " for branch " + convergenceBranch
            };
        }

        table.add(row);
    }

    table.finalize();
    return table;
}

std::unique_ptr<HistogramKernel> RootKernelReader::readHistogramKernel(
    const std::filesystem::path& filePath,
    const char* histogramName
)
{
    std::unique_ptr<TFile> file{TFile::Open(filePath.string().c_str(), "READ")};

    if (!file || file->IsZombie())
    {
        throw std::runtime_error{"Cannot open response calibration: " + filePath.string()};
    }

    TH3D* histogram = file->Get<TH3D>(histogramName);

    if (histogram == nullptr)
    {
        throw std::runtime_error{"Cannot find empirical response histogram: " +
                                 std::string{histogramName}};
    }

    std::vector<Decimal> energies;
    std::vector<Decimal> angles;
    std::vector<Decimal> deltas;

    for (int bin = 1; bin <= histogram->GetNbinsX(); ++bin)
    {
        energies.push_back(histogram->GetXaxis()->GetBinCenter(bin));
    }
    for (int bin = 1; bin <= histogram->GetNbinsY(); ++bin)
    {
        angles.push_back(histogram->GetYaxis()->GetBinCenter(bin));
    }
    for (int bin = 1; bin <= histogram->GetNbinsZ(); ++bin)
    {
        deltas.push_back(histogram->GetZaxis()->GetBinCenter(bin));
    }

    std::vector<Decimal> density;
    density.reserve(energies.size() * angles.size() * deltas.size());

    for (int energy = 1; energy <= histogram->GetNbinsX(); ++energy)
    {
        for (int angle = 1; angle <= histogram->GetNbinsY(); ++angle)
        {
            for (int delta = 1; delta <= histogram->GetNbinsZ(); ++delta)
            {
                density.push_back(histogram->GetBinContent(energy, angle, delta));
            }
        }
    }

    return std::make_unique<HistogramKernel>(
        std::move(energies),
        std::move(angles),
        std::move(deltas),
        std::move(density)
    );
}
