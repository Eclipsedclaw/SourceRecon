#ifndef DOPPLER_V7_EXPERIMENT_ROOT_WRITER_HH
#define DOPPLER_V7_EXPERIMENT_ROOT_WRITER_HH

#include "ExperimentRecord.hh"

#include <memory>

class ConfigManager;
class TFile;
class TH1D;
class TTree;

class ExperimentRootWriter
{
public:
    explicit ExperimentRootWriter(const ConfigManager& config);
    ~ExperimentRootWriter();

    void open();
    void write(const ExperimentRecord& record);
    void finish(const ExperimentCounters& counters);

private:
    const ConfigManager* config_{};
    std::unique_ptr<TFile> file_;
    TTree* tree_{};
    TH1D* truthArmHistogram_{};
    TH1D* detectorArmHistogram_{};
    TH1D* truthEnergyResidualHistogram_{};
    TH1D* detectorEnergyResidualHistogram_{};
    ExperimentRecord buffer_;
};

#endif
