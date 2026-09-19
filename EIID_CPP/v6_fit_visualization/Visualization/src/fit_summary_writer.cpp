#include "fit_summary_writer.h"

#include <nlohmann/json.hpp>

#include <filesystem>
#include <fstream>
#include <stdexcept>

void FitSummaryWriter::write(
    const FitAnalysisResult& analysis,
    const VisConfig& config
)
{
    nlohmann::json warnings = nlohmann::json::array();

    if (!analysis.preliminaryEnergy.fitConverged)
    {
        warnings.push_back(
            "Preliminary ROOT energy fit failed; moment fallback was used."
        );
    }

    if (!analysis.direction.fitConverged)
    {
        warnings.push_back(
            "ROOT direction fit failed; moment fallback was used."
        );
    }

    if (!analysis.finalEnergy.fitConverged)
    {
        warnings.push_back(
            "Final ROOT energy fit failed; moment fallback was used."
        );
    }

    if (analysis.direction.underResolved)
    {
        warnings.push_back(
            "Direction Gaussian width is below the mean HEALPix pixel scale."
        );
    }

    if (!analysis.direction.truthInsideLocalView)
    {
        warnings.push_back(
            "Truth direction lies outside the configured local direction-fit view."
        );
    }

    const nlohmann::json document{
        {"schema_version", 1},
        {"methods", {
            {"energy", "local_gaussian_plus_constant_background"},
            {"direction", "local_tangent_plane_elliptical_gaussian"},
            {"uncertainty_note", "MLEM image weights are not independent event counts; fit widths are descriptive."}
        }},
        {"truth", {
            {"theta_degree", config.truth().thetaDegree},
            {"phi_degree", config.truth().phiDegree},
            {"energy_MeV", config.truth().energyMeV}
        }},
        {"energy_fit", {
            {"fit_converged", analysis.finalEnergy.fitConverged},
            {"fit_status", analysis.finalEnergy.fitStatus},
            {"fit_min_MeV", analysis.finalEnergy.fitMinMeV},
            {"fit_max_MeV", analysis.finalEnergy.fitMaxMeV},
            {"direction_gate_radius_degree", analysis.finalEnergy.directionGateRadiusDegree},
            {"mean_MeV", analysis.finalEnergy.meanMeV},
            {"bias_MeV", analysis.finalEnergy.truthBiasMeV},
            {"sigma_MeV", analysis.finalEnergy.sigmaMeV},
            {"fwhm_MeV", analysis.finalEnergy.fwhmMeV},
            {"relative_fwhm", analysis.finalEnergy.relativeFwhm}
        }},
        {"direction_fit", {
            {"fit_converged", analysis.direction.fitConverged},
            {"fit_status", analysis.direction.fitStatus},
            {"theta_degree", analysis.direction.fittedThetaDegree},
            {"phi_degree", analysis.direction.fittedPhiDegree},
            {"angular_bias_degree", analysis.direction.angularBiasDegree},
            {"sigma_major_degree", analysis.direction.sigmaMajorDegree},
            {"sigma_minor_degree", analysis.direction.sigmaMinorDegree},
            {"ellipse_angle_degree", analysis.direction.ellipseAngleDegree},
            {"healpix_nside", analysis.direction.healpixNside},
            {"mean_pixel_scale_degree", analysis.direction.pixelScaleDegree},
            {"under_resolved", analysis.direction.underResolved}
        }},
        {"containment", {
            {"R50_degree", analysis.containment.r50Degree},
            {"R68_degree", analysis.containment.r68Degree},
            {"R90_degree", analysis.containment.r90Degree}
        }},
        {"warnings", warnings}
    };
    const std::filesystem::path outputPath =
        config.outputDirectory() / "fit_summary.json";
    std::ofstream output{outputPath};

    if (!output)
    {
        throw std::runtime_error{
            "Cannot create fit summary: " + outputPath.string()
        };
    }

    output << document.dump(4) << '\n';

    if (!output)
    {
        throw std::runtime_error{
            "Failed while writing fit summary: " + outputPath.string()
        };
    }
}
