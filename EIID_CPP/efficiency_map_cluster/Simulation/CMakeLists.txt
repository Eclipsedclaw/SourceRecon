cmake_minimum_required(VERSION 3.20)
if(NOT DEFINED EFF_PROJECT_ROOT)
    project(EfficiencySimulation LANGUAGES CXX)
    include(CTest)
    set(EFF_BUILD_SIMULATION ON CACHE BOOL "" FORCE)
    set(EFF_BUILD_MERGER OFF CACHE BOOL "" FORCE)
    add_subdirectory(.. suite)
    return()
endif()
add_executable(efficiency_simulator
    src/main.cpp src/TaskRunner.cpp src/ActionInitialization.cpp src/EfficiencyRun.cpp src/RunAction.cpp
    src/EventAction.cpp src/PrimaryGeneratorAction.cpp src/SimulationGrid.cpp
    src/AutoBoundingConePolicy.cpp src/Ch2CenteredHemisphereSource.cpp src/DetectorGeometryInfo.cpp
    src/DetectorConstruction.cc src/DetectorMessenger.cc src/MyPhysicsList.cc src/TrackerHit.cc src/TrackerSD.cc)
target_include_directories(efficiency_simulator PRIVATE include "${EFF_GENERATED_DIR}")
# 只链接输运所需 Geant4 库；不创建 UI/Vis executive，不引入 Qt/OpenGL 驱动。
target_link_libraries(efficiency_simulator PRIVATE eff_root_io eff_healpix
    Geant4::G4run Geant4::G4event Geant4::G4processes Geant4::G4digits_hits
    Geant4::G4particles Geant4::G4geometry Geant4::G4materials Geant4::G4tracking)
target_compile_options(efficiency_simulator PRIVATE -Wall -Wextra -Wpedantic)
