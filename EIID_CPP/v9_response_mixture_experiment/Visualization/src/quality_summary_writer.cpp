#include "quality_summary_writer.h"

#include <nlohmann/json.hpp>

#include <filesystem>
#include <fstream>
#include <stdexcept>

namespace
{
nlohmann::json gaussianEnergyDocument(const GaussianEnergyFit& fit)
{
    return nlohmann::json{
        {"enabled", fit.enabled},
        {"converged", fit.converged},
        {"ROOT_fit_status", fit.status},
        {"fit_min_MeV", fit.fitMinMeV},
        {"fit_max_MeV", fit.fitMaxMeV},
        {"mean_MeV", fit.meanMeV},
        {"sigma_MeV", fit.sigmaMeV}
    };
}

nlohmann::json energyDocument(const EnergyMetrics& metrics)
{
    return nlohmann::json{
        {"peak", {
            {"energy_MeV", metrics.peakEnergyMeV},
            {"bias_MeV", metrics.peakBiasMeV},
            {"interpolation", "three_point_parabola"}
        }},
        {"direct_FWHM", {
            {"available", metrics.directFwhmAvailable},
            {"left_half_maximum_MeV", metrics.leftHalfMaximumMeV},
            {"right_half_maximum_MeV", metrics.rightHalfMaximumMeV},
            {"width_MeV", metrics.directFwhmMeV},
            {"relative_to_peak", metrics.relativeDirectFwhm}
        }},
        {"shortest_intensity_interval", {
            {"fraction", metrics.intervalFraction},
            {"low_MeV", metrics.intervalLowMeV},
            {"high_MeV", metrics.intervalHighMeV},
            {"width_MeV", metrics.intervalWidthMeV}
        }},
        {"global_moments", {
            {"mean_MeV", metrics.momentMeanMeV},
            {"mean_bias_MeV", metrics.momentMeanBiasMeV},
            {"sigma_MeV", metrics.momentSigmaMeV}
        }},
        {"direction_gate_radius_degree", metrics.directionGateRadiusDegree},
        {"optional_Gaussian", gaussianEnergyDocument(metrics.gaussian)}
    };
}
}

void QualitySummaryWriter::write(
    const QualityAnalysisResult& analysis,
    const VisConfig& config
)
{
    nlohmann::json warnings = nlohmann::json::array();
    nlohmann::json notes = nlohmann::json::array();

    if (!analysis.directionGatedEnergy.directFwhmAvailable)
    {
        warnings.push_back(
            "Direct energy FWHM is unavailable because one or both half-height crossings are outside the sampled range."
        );
    }

    if (analysis.direction.underResolved)
    {
        warnings.push_back(
            "The minor direction RMS is below the mean HEALPix pixel scale; quote it only as under-resolved."
        );
    }

    if (!analysis.direction.truthInsideLocalView)
    {
        warnings.push_back(
            "The truth direction lies outside the configured local direction view."
        );
    }

    if (analysis.directionGatedEnergy.gaussian.enabled &&
        !analysis.directionGatedEnergy.gaussian.converged)
    {
        notes.push_back(
            "The optional energy Gaussian fit did not converge; all primary energy metrics remain valid because they do not use that fit."
        );
    }

    if (analysis.direction.gaussian.enabled &&
        !analysis.direction.gaussian.converged)
    {
        notes.push_back(
            "The optional direction Gaussian fit did not converge; centroid and covariance metrics remain valid because they do not use that fit."
        );
    }

    const nlohmann::json document{
        {"schema_version", 2},
        {"methods", {
            {"energy_peak", "three_point_parabolic_interpolation"},
            {"energy_width", "direct_baseline_corrected_half_height_crossings"},
            {"energy_interval", "shortest_contiguous_intensity_interval"},
            {"direction_center", "background_subtracted_weighted_tangent_plane_centroid"},
            {"direction_width", "weighted_tangent_plane_covariance_eigenvalues"},
            {"Gaussian_role", "optional_diagnostic_only"}
        }},
        {"truth", {
            {"theta_degree", config.truth().thetaDegree},
            {"phi_degree", config.truth().phiDegree},
            {"energy_MeV", config.truth().energyMeV}
        }},
        {"full_sky_energy", energyDocument(analysis.fullSkyEnergy)},
        {"direction_gated_energy", energyDocument(
            analysis.directionGatedEnergy
        )},
        {"direction", {
            {"centroid_theta_degree", analysis.direction.centroidThetaDegree},
            {"centroid_phi_degree", analysis.direction.centroidPhiDegree},
            {"angular_bias_degree", analysis.direction.angularBiasDegree},
            {"RMS_major_degree", analysis.direction.rmsMajorDegree},
            {"RMS_minor_degree", analysis.direction.rmsMinorDegree},
            {"ellipse_angle_degree", analysis.direction.ellipseAngleDegree},
            {"energy_gate_low_MeV", analysis.direction.energyGateLowMeV},
            {"energy_gate_high_MeV", analysis.direction.energyGateHighMeV},
            {"healpix_nside", analysis.direction.healpixNside},
            {"mean_pixel_scale_degree", analysis.direction.pixelScaleDegree},
            {"under_resolved", analysis.direction.underResolved},
            {"optional_Gaussian", {
                {"enabled", analysis.direction.gaussian.enabled},
                {"converged", analysis.direction.gaussian.converged},
                {"ROOT_fit_status", analysis.direction.gaussian.status},
                {"theta_degree", analysis.direction.gaussian.thetaDegree},
                {"phi_degree", analysis.direction.gaussian.phiDegree},
                {"sigma_major_degree", analysis.direction.gaussian.sigmaMajorDegree},
                {"sigma_minor_degree", analysis.direction.gaussian.sigmaMinorDegree}
            }}
        }},
        {"containment", {
            {"R50_degree", analysis.containment.r50Degree},
            {"R68_degree", analysis.containment.r68Degree},
            {"R90_degree", analysis.containment.r90Degree}
        }},
        {"warnings", warnings},
        {"notes", notes}
    };
    const std::filesystem::path outputPath =
        config.outputDirectory() / "quality_summary.json";
    std::ofstream output{outputPath};

    if (!output)
    {
        throw std::runtime_error{
            "Cannot create quality summary: " + outputPath.string()
        };
    }

    output << document.dump(4) << '\n';

    if (!output)
    {
        throw std::runtime_error{
            "Failed while writing quality summary: " + outputPath.string()
        };
    }
}
