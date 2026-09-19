#include "plot_raw_efficiency_map.C"
#include <fstream>

void run_efficiency_slice()
{
    try
    {
        const char* input = "input/raw_efficiency_master.root";
        TFile file{input, "READ"};
        if (file.IsZombie() || file.TestBit(TFile::kRecovered))
            throw std::runtime_error{"Input ROOT is invalid or recovered"};
        const auto nside = requireObject<TParameter<int>>(file, "healpix_nside").GetVal();
        const auto energies = requireObject<TParameter<Long64_t>>(file, "energy_count").GetVal();
        const auto directions = requireObject<TParameter<Long64_t>>(file, "direction_count").GetVal();
        const auto emin = requireObject<TParameter<double>>(file, "energy_min_MeV").GetVal();
        const auto emax = requireObject<TParameter<double>>(file, "energy_max_MeV").GetVal();
        if (nside != 16 || directions != 3072 || energies != 1 || emin != 0.662 || emax != 0.662)
            throw std::runtime_error{"Expected the completed Nside=16 monoenergetic 0.662 MeV slice"};
        TTreeReader reader{"RawEfficiency", &file};
        TTreeReaderValue<ULong64_t> index{reader, "cell_index"};
        TTreeReaderValue<ULong64_t> emitted{reader, "emitted_count"};
        TTreeReaderValue<ULong64_t> valid{reader, "valid_count"};
        TTreeReaderValue<Double_t> efficiency{reader, "efficiency"};
        TTreeReaderValue<Double_t> fraction{reader, "cone_solid_angle_fraction"};
        ULong64_t totalEmitted = 0, totalValid = 0;
        std::size_t active = 0, positive = 0;
        std::vector<bool> seen(3072, false);
        std::vector<double> activeEfficiencies;
        ULong64_t minimumValid = std::numeric_limits<ULong64_t>::max(), maximumValid = 0;
        while (reader.Next())
        {
            if (*index >= seen.size() || seen[*index] || *valid > *emitted ||
                !std::isfinite(*efficiency) || !std::isfinite(*fraction) ||
                *efficiency < 0 || *fraction < 0 || *fraction > 1)
                throw std::runtime_error{"Invalid or duplicate efficiency row"};
            seen[*index] = true;
            const double expected = *emitted ? static_cast<double>(*valid) / *emitted * *fraction : 0.0;
            if (std::abs(*efficiency - expected) > 1e-13 * std::max(expected, 1e-30))
                throw std::runtime_error{"Efficiency differs from raw k/N times cone fraction"};
            if (*emitted)
            {
                if (*emitted != 1000000 || *index < 1504 || *fraction <= 0)
                    throw std::runtime_error{"Unexpected exposure in the front-hemisphere slice"};
                ++active;
                positive += *efficiency > 0;
                minimumValid = std::min(minimumValid, *valid);
                maximumValid = std::max(maximumValid, *valid);
                activeEfficiencies.push_back(*efficiency);
            }
            else if (*index >= 1504 || *valid != 0 || *efficiency != 0 || *fraction != 0)
                throw std::runtime_error{"Unexpected unexposed cell"};
            totalEmitted += *emitted;
            totalValid += *valid;
        }
        if (reader.GetEntryStatus() != TTreeReader::kEntryBeyondEnd ||
            !std::all_of(seen.begin(), seen.end(), [](bool value) { return value; }) ||
            active != 1568 || positive != 1568 || totalEmitted != 1568000000ULL || totalValid != 164535)
            throw std::runtime_error{"Slice totals differ from the validated cluster merge"};

        std::sort(activeEfficiencies.begin(), activeEfficiencies.end());
        std::ostringstream summary;
        summary << std::setprecision(12)
                << "Input: " << input << "\nEnergy: 0.662 MeV (exact layer; no energy interpolation)\n"
                << "HEALPix Nside: 16, RING; full-sky rows: 3072\n"
                << "Camera front: -Z at longitude=0, latitude=0\n"
                << "Source distance from ch2 centre: "
                << requireObject<TParameter<double>>(file, "source_radius_mm").GetVal() << " mm\n"
                << "Simulated cells: " << active << "\nNonzero simulated cells: " << positive
                << "\nUnexposed cells: 1504 (grey; not measured zero)\n"
                << "Total emitted: " << totalEmitted << "\nValid two-layer triggers: " << totalValid
                << "\nValid triggers per active cell: min=" << minimumValid << ", max=" << maximumValid
                << "\nAbsolute efficiency: min=" << activeEfficiencies.front()
                << ", median=" << 0.5 * (activeEfficiencies[783] + activeEfficiencies[784])
                << ", max=" << activeEfficiencies.back()
                << "\nFormula checked: efficiency = valid_count/emitted_count * cone_solid_angle_fraction\n"
                << "No pseudo-count, no spatial smoothing, no energy interpolation.\n"
                << "Raster samples the HEALPix pixel value; plotting resolution is not detector resolution.\n"
                << "Viridis: dark purple = LOW, yellow = HIGH. Rectangular log and skymap share range.\n";
        std::cout << summary.str();
        gSystem->mkdir("figures", true);
        std::ofstream output{"figures/summary.txt"};
        output << summary.str();
        output.close();
        if (!output) throw std::runtime_error{"Could not write summary"};
        plot_raw_efficiency_map(input, "RawEfficiency", 0.662, "figures", true);
    }
    catch (const std::exception& error)
    {
        std::cerr << "Efficiency visualization failed: " << error.what() << '\n';
        gSystem->Exit(1);
    }
}
