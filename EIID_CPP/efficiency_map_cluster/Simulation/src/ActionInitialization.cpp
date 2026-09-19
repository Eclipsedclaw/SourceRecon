#include "ActionInitialization.hh"
#include "EventAction.hh"
#include "PrimaryGeneratorAction.hh"

ActionInitialization::ActionInitialization(const Campaign& campaign, const SimulationGrid& grid,
                                           const RunContext& context, std::shared_ptr<const ISourceGeometry> source,
                                           std::shared_ptr<const IEmissionConePolicy> cone,
                                           const nlohmann::json& software)
    : campaign_{campaign}, grid_{grid}, context_{context}, source_{std::move(source)}, cone_{std::move(cone)},
      software_{software}
{
}

RunAction* ActionInitialization::makeRunAction() const
{
    return new RunAction{campaign_, grid_, context_, source_, cone_, software_};
}

void ActionInitialization::BuildForMaster() const
{
    // 主线程只汇总，不安装粒子枪和 EventAction。
    SetUserAction(makeRunAction());
}

void ActionInitialization::Build() const
{
    auto* run = makeRunAction();
    SetUserAction(run);
    SetUserAction(new PrimaryGeneratorAction{campaign_.config, grid_, context_, source_, cone_});
    SetUserAction(new EventAction{campaign_.config, grid_, context_, *run});
}
