#ifndef EIID_V10_BENCHMARK_RUNNER_H
#define EIID_V10_BENCHMARK_RUNNER_H

class BenchmarkConfig;

class BenchmarkRunner
{
public:
    static void run(const BenchmarkConfig& config);
};

#endif
