#include <TFile.h>
#include <TTree.h>
#include <TH1D.h>
#include <TTreeReader.h>
#include <TTreeReaderValue.h>
#include <TCanvas.h>
#include <cmath>
#include <iostream>
#include <memory>
#include <random>

void Challenge_AngleAnalysis()
{
    auto Open = std::unique_ptr<TFile>{TFile::Open("challenge_kinematics.root","RECREATE")};
    if(!Open||Open->IsZombie())
    {
        std::cerr << "Failed to create challenge_kinematics.root! :(";
        return;
    }//保证Open成功被创建
    auto* Tree = new TTree("Particles","Just a Practice lol");
    Tree->SetDirectory(Open.get());//显示地把Tree挂到Open下，只是为了练习，实际上在这里可以省略

    double px{0.0},py{0.0};
    Tree->Branch("px",&px);
    Tree->Branch("Supercalifragilisticexpialidocious_py",&py);
    //这里是地址传参，所以Tree会永远铭记px和py的，可谓春蚕到死丝方尽，蜡炬成灰泪始干！

    std::mt19937_64 randomEngine{1145141919810};

    std::normal_distribution<double> gaussDrist(0.0 , 2.0);

    const std::size_t TotalNumber{5000};
    for(std::size_t i = 0U;i<TotalNumber;++i)
    {
        px = gaussDrist(randomEngine);
        py = gaussDrist(randomEngine);
        Tree->Fill();
    }

    //---------------------------------------------------------------------------------------------------------------------------

    Tree->Write();//让Tree把basket里没拉干净的shit揩干净
    Open->Close();//停止写入Open
    Open.reset();//相当于执行Open->~TFile(); free Open.get(); 实际上，这三句留着一句就够了，但是不会执行 Open->~std::unique_ptr;

    //---------------------------------------------------------------------------------------------------------------------------

    Open = std::unique_ptr<TFile>{TFile::Open("challenge_kinematics.root","READ")};

    if(!Open||Open->IsZombie())
    {
        std::cerr << "Failed to read challenge_kinematics.root! :(";
        return;
    }//防止熊孩子

    TTree* const ReadTree = Open->Get<TTree>("Particles");

    if(!ReadTree)
    {
        std::cerr << "Failed to find tree named \"Particles\" in challenge_kinematics.root! :(";
        return;
    }//防熊

    //画直方图
    auto His = std::make_unique<TH1D>
    (
        "h_phi",
        "Azimuthal Angle Distribution; #phi [rad]; Events / bin",
        50,
        -M_PI,
        M_PI
    );
    His->SetDirectory(nullptr);
    His->Sumw2();
    TTreeReader ReaderForOpen{ReadTree};
    TTreeReaderValue<double> Read_px{ReaderForOpen,"px"};
    TTreeReaderValue<double> Read_py{ReaderForOpen,"Supercalifragilisticexpialidocious_py"};

    while(ReaderForOpen.Next())
    {
        const double phi{std::atan2(*Read_py,*Read_px)};
        His->Fill(phi);
    }

    auto Canv = std::make_unique<TCanvas>
    (
        "Canv1",
        "MyFirstCanvasForPractice",
        800,
        600
    );

    Canv->cd(); //显示调用Canv，实际上可省略

    His->Draw("E");
    Canv->Modified();
    Canv->Update();
    Canv->SaveAs("output.png");
}