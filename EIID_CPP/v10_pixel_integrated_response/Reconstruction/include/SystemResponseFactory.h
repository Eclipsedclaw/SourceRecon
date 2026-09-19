#ifndef EIID_V10_SYSTEM_RESPONSE_FACTORY_H
#define EIID_V10_SYSTEM_RESPONSE_FACTORY_H

#include <memory>

class IGrid;
class IResponseKernel;
class ISystemResponseEvaluator;
class ReconConfig;

class SystemResponseFactory
{
public:
    static std::unique_ptr<ISystemResponseEvaluator> create(
        const ReconConfig& config,
        const IGrid& grid,
        const IResponseKernel& responseKernel
    );
};

#endif
