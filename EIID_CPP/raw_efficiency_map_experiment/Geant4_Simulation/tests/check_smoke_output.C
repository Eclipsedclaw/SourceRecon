// 只读核对小测试的真实输出；全零触发会让 make smoke 报验收失败，但不删除数据。
#include <TFile.h>
#include <TParameter.h>
#include <TSystem.h>
#include <TTree.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>

void check_smoke_output(const char* path = "runs/smoke_test/raw_efficiency_master.root")
{
    int exitCode = 0;
    try
    {
        TFile file{path, "READ"};
        if (file.IsZombie())
        {
            throw std::runtime_error{"Cannot open smoke-test ROOT file."};
        }
        auto* tree = file.Get<TTree>("RawEfficiency");
        auto* requested = file.Get<TParameter<Long64_t>>("requested_event_count");
        auto* directions = file.Get<TParameter<Long64_t>>("direction_count");
        auto* energies = file.Get<TParameter<Long64_t>>("energy_count");
        if (tree == nullptr || requested == nullptr || directions == nullptr || energies == nullptr)
        {
            throw std::runtime_error{"Missing test metadata: rebuild and rerun with the updated simulator."};
        }
        if (requested->GetVal() <= 0 || directions->GetVal() <= 0 || energies->GetVal() <= 0)
        {
            throw std::runtime_error{"Invalid grid or requested event count."};
        }

        const auto cellCount = static_cast<std::size_t>(directions->GetVal() * energies->GetVal());
        std::vector<bool> seen(cellCount, false);
        std::uint64_t emittedTotal = 0;
        std::uint64_t validTotal = 0;
        std::size_t simulatedCells = 0;
        std::size_t positiveCells = 0;
        TTreeReader reader{tree};
        TTreeReaderValue<ULong64_t> index{reader, "cell_index"};
        TTreeReaderValue<ULong64_t> emitted{reader, "emitted_count"};
        TTreeReaderValue<ULong64_t> valid{reader, "valid_count"};
        TTreeReaderValue<Double_t> fraction{reader, "cone_solid_angle_fraction"};
        TTreeReaderValue<Double_t> efficiency{reader, "efficiency"};

        while (reader.Next())
        {
            if (*index >= cellCount || seen[static_cast<std::size_t>(*index)])
            {
                throw std::runtime_error{"Duplicate or invalid cell index."};
            }
            seen[static_cast<std::size_t>(*index)] = true;
            if (*valid > *emitted || !std::isfinite(*fraction) || *fraction <= 0.0 || *fraction > 1.0)
            {
                throw std::runtime_error{"Invalid event counts or emission-cone fraction."};
            }
            // 验证实际写盘值确实是 k/N 乘发射锥比例，零计数不能混入伪计数。
            const double expected = *emitted == 0 ? 0.0 : static_cast<double>(*valid) / *emitted * *fraction;
            if (!std::isfinite(*efficiency) || std::abs(*efficiency - expected) > 1.0e-12 * std::max(expected, 1.0e-300))
            {
                throw std::runtime_error{"ROOT efficiency differs from the raw k/N estimate."};
            }
            emittedTotal += *emitted;
            validTotal += *valid;
            simulatedCells += *emitted > 0 ? 1 : 0;
            positiveCells += *valid > 0 ? 1 : 0;
        }
        if (reader.GetEntryStatus() != TTreeReader::kEntryBeyondEnd ||
            std::find(seen.begin(), seen.end(), false) != seen.end())
        {
            throw std::runtime_error{"Incomplete ROOT data or reader error."};
        }

        std::cout << "Smoke-test ROOT check:\n"
                  << "  Simulated cells: " << simulatedCells << '\n'
                  << "  Completed events: " << emittedTotal << '\n'
                  << "  Valid two-layer triggers: " << validTotal << '\n'
                  << "  Cells with valid triggers: " << positiveCells << '\n';
        if (emittedTotal != static_cast<std::uint64_t>(requested->GetVal()))
        {
            throw std::runtime_error{"Completed event count does not match the requested count."};
        }
        if (validTotal == 0)
        {
            throw std::runtime_error{"No valid triggers. Inspect actual particle and layer counters; do not launch a large run yet."};
        }
        std::cout << "SMOKE TEST PASSED: nonzero triggers, complete counts, raw efficiency verified.\n";
    }
    catch (const std::exception& error)
    {
        std::cerr << "SMOKE TEST FAILED: " << error.what() << '\n';
        exitCode = 1;
    }
    // 此处局部 ROOT 对象已析构；明确把验收状态返回给 make。
    gSystem->Exit(exitCode);
}
