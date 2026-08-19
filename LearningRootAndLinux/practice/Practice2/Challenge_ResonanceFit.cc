#include <cmath>
#include <iostream>
#include <memory>
#include <random>

#include <TTree.h>
#include <TFile.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>
#include <TH1D.h>
#include <TF1.h>
#include <TCanvas.h>
#include <TStyle.h>
#include <TFitResult.h>
#include <TFitResultPtr.h>
 
void ReadProcess()
{
    //Recreate一个.root文件
    auto File = std::unique_ptr<TFile>{TFile::Open("resonance_data.root","RECREATE")}; 
    if(!File || File -> IsZombie())
    {
        std::cerr << "Failed to recreate a .root File!" ;
        return; 
    }
    
    //按照要求新建DecayTree并把他们显式挂到File下，再在DecayTree下新建四个Branch
    TTree* DecayTree = new TTree("DecayTree","Decayed particles");
    DecayTree -> SetDirectory(File.get());
    double Ea, Eb, pza, pzb;
    DecayTree -> Branch("Ea",&Ea);
    DecayTree -> Branch("Eb",&Eb);
    DecayTree -> Branch("pza",&pza);
    DecayTree -> Branch("pzb",&pzb);

    //新建随机数生成器引擎，以及两个高斯分布器
    std::mt19937_64 randomEngine{20260817};
    std::normal_distribution<double> DistributionForE{3.10,0.05};
    std::normal_distribution<double> DistributionForPz{0.0,1.0};
    
    //填充DeacyTree
    const std::size_t EventCounts = 10000;
    for(std::size_t i = 0 ; i < EventCounts ; ++i)
    {
        const double E = DistributionForE(randomEngine);
        const double Pz = DistributionForPz(randomEngine);
        const double Etot = std::hypot(E, Pz);
        Ea = 0.5 * Etot;
        Eb = Etot - Ea;
        pza = 0.5 * Pz;
        pzb = Pz - pza;
        DecayTree -> Fill();
    }

    //收尾工作
    DecayTree -> Write();
    File.reset();
}

void PrintProcess()
{
    //RAII风格读取File
    auto File = std::unique_ptr<TFile>{TFile::Open("resonance_data.root","READ")};
    if(!File || File -> IsZombie())
    {
        std::cerr << "Failed to open resonance_data.root!";
        return;
    }

    //获取DecayTree
    TTree* const DecayedParticles = File -> Get<TTree>("DecayTree");
    if(!DecayedParticles)
    {
        std::cerr << "Failed to get DecayedParticles!" ;
        return;
    }

    //设置读取器
    TTreeReader TreeReader{DecayedParticles};
    TTreeReaderValue<double> ReadEa{TreeReader,"Ea"};
    TTreeReaderValue<double> ReadEb{TreeReader,"Eb"};
    TTreeReaderValue<double> Readpza{TreeReader,"pza"};
    TTreeReaderValue<double> Readpzb{TreeReader,"pzb"};

    //生成并初始化直方图
    auto His = std::make_unique<TH1D>
    (
        "h_mass",
        "Invariant Mass Reconstruction;M_{inv} [GeV];Events / (0.02 GeV)",
        60,
        2.5,
        3.7
    );
    His -> SetDirectory(nullptr);
    His -> Sumw2();

    //填写直方图
    std::size_t acceptedEvents{0};
    while(TreeReader.Next())
    {
        // His -> Fill(hypot(*ReadEa + *ReadEb ,*Readpza + *Readpzb)); //千万不要忘记给数值读取器解引用！！！！！
        const double Etot = *ReadEa + *ReadEb;
        const double Pztot = *Readpza + *Readpzb;
        const double Minv = std::sqrt(Etot * Etot - Pztot * Pztot);
        His->Fill(Minv);
        ++acceptedEvents;
    }
    if(acceptedEvents == 0U)
    {
        std::cerr << "No Events" ;
        return;
    }
    
    //高斯拟合
    TF1 GaussianFitter
    (
        "GaussianFitter",
        "gaus",
        2.9,
        3.3
    );
    GaussianFitter.SetParameters
    (
        His -> GetMaximum(),
        His -> GetMean(),
        His -> GetStdDev()
    );

    //定义并初始化canvas画布
    auto canvas = std::make_unique<TCanvas>
    (
        "Canvas",
        "Display for Decayed Particles",
        900,
        650
    );
    gStyle -> SetOptFit(1111); 

    //画图
    His -> Draw("E");
    const TFitResultPtr fitResult{His->Fit(&GaussianFitter, "S")};
    
    //后处理并输出
    const int fitStatus{static_cast<int>(fitResult)};
    if (fitStatus != 0) 
    {
        std::cerr << "Warning: fit did not converge; status = " << fitStatus << '\n';
    }
    else
    {
        const double amplitude{GaussianFitter.GetParameter(0)};
        const double mean{GaussianFitter.GetParameter(1)};
        const double sigma{GaussianFitter.GetParameter(2)};

        const double amplitudeError{GaussianFitter.GetParError(0)};
        const double meanError{GaussianFitter.GetParError(1)};
        const double sigmaError{GaussianFitter.GetParError(2)};

        std::cout << "Fit succeeded for " << acceptedEvents << " events:\n"
                  << "  amplitude = " << amplitude << " +/- " << amplitudeError << '\n'
                  << "  mean      = " << mean << " +/- " << meanError << '\n'
                  << "  sigma     = " << sigma << " +/- " << sigmaError << '\n';
    }

    canvas->Modified();
    canvas->Update();
    canvas->SaveAs("resonance_fit.png");
}

int main()
{
    ReadProcess();
    PrintProcess();
    return 0;
}