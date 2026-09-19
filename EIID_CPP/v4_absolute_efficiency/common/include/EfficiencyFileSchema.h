#ifndef EIID_V4_EFFICIENCY_FILE_SCHEMA_H
#define EIID_V4_EFFICIENCY_FILE_SCHEMA_H

namespace EfficiencyFileSchema
{
inline constexpr const char* cellIndexBranch = "cell_index";
inline constexpr const char* efficiencyBranch = "sensitivity";
inline constexpr const char* nsideMetadata = "healpix_nside";
inline constexpr const char* orderingMetadata = "healpix_ordering";
inline constexpr const char* directionCountMetadata = "direction_count";
inline constexpr const char* energyCountMetadata = "energy_count";
inline constexpr const char* energyMinMetadata = "energy_min_MeV";
inline constexpr const char* energyMaxMetadata = "energy_max_MeV";
inline constexpr const char* sourceRadiusMetadata = "source_radius_mm";
inline constexpr const char* definitionMetadata = "efficiency_definition";
}

#endif
