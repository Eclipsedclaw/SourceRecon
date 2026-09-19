#ifndef EIID_V7_EFFICIENCY_FILE_SCHEMA_H
#define EIID_V7_EFFICIENCY_FILE_SCHEMA_H

namespace EfficiencyFileSchema
{
inline constexpr const char* cellIndexBranch = "cell_index";
inline constexpr const char* efficiencyBranch = "efficiency";
inline constexpr const char* regularizedEfficiencyBranch = "regularized_efficiency";
inline constexpr const char* emittedCountBranch = "emitted_count";
inline constexpr const char* validCountBranch = "valid_count";
inline constexpr const char* coneSolidAngleFractionBranch = "cone_solid_angle_fraction";
inline constexpr const char* nsideMetadata = "healpix_nside";
inline constexpr const char* orderingMetadata = "healpix_ordering";
inline constexpr const char* directionCountMetadata = "direction_count";
inline constexpr const char* energyCountMetadata = "energy_count";
inline constexpr const char* energyMinMetadata = "energy_min_MeV";
inline constexpr const char* energyMaxMetadata = "energy_max_MeV";
inline constexpr const char* sourceRadiusMetadata = "source_radius_mm";
inline constexpr const char* definitionMetadata = "efficiency_definition";
inline constexpr const char* efficiencyDefinition =
    "isotropic_point_source_absolute_detection_efficiency_4pi_raw_k_over_N";
}

#endif
