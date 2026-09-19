#ifndef EIID_V8_CALIBRATION_SCHEMA_H
#define EIID_V8_CALIBRATION_SCHEMA_H

#include <string_view>

namespace CalibrationSchema
{
inline constexpr std::string_view eventId{"event_id"};
inline constexpr std::string_view detectorKinematicsValid{
    "detector_kinematics_valid"
};
inline constexpr std::string_view truthScatterAngle{
    "truth_theta_kin_degree"
};
inline constexpr std::string_view detectorScatterAngle{
    "detector_theta_kin_degree"
};
inline constexpr std::string_view truthArm{"truth_arm_degree"};
inline constexpr std::string_view detectorArm{"detector_arm_degree"};
inline constexpr std::string_view sourceEnergyMetadata{"source_energy_MeV"};

std::string_view description() noexcept;
}

#endif
