// 1. 创建文件和 TTree 对象
TFile* file = new TFile("physics_data.root", "RECREATE");
TTree* tree = new TTree("MyTree", "A simple example tree");

// 2. 准备 C++ 变量
double px, py;
int event_id;

// 3. 将变量的内存地址绑定到 TTree 的分支上
// 参数：分支名, 绑定的变量地址
tree->Branch("px", &px);
tree->Branch("py", &py);
tree->Branch("event_id", &event_id);

// 4. 事件循环 (模拟 10 万个粒子事件)
for (int i = 0; i < 100000; ++i) {
    // 更新 C++ 变量的值 (通常这些值来自 Geant4 模拟)
    event_id = i;
    px = 1.5 * i; // 随便造点假数据
    py = 2.0 * i;
    
    // 5. 调用 Fill()：ROOT 会读取绑定变量当前的值，将其作为新的一行存入硬盘
    tree->Fill(); 
}

// 6. 将内存中的树结构安全写入文件并清理
tree->Write();
file->Close();

//@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

// 1. 打开文件
TFile* file = TFile::Open("physics_data.root");

// 2. 为目标树创建一个 TTreeReader
TTreeReader reader("MyTree", file);[cite: 1]

// 3. 将读取器映射到特定的分支，必须明确指定 C++ 数据类型 (类似智能指针)
TTreeReaderValue<double> val_px(reader, "px");[cite: 1]
TTreeReaderValue<double> val_py(reader, "py");[cite: 1]

// 4. 事件循环遍历
// reader.Next() 会自动将内部游标移到下一行，并在读完时返回 false
while (reader.Next()) {[cite: 1]
    
    // TTreeReaderValue 重载了解引用运算符 (*)
    // 你可以像使用普通指针一样获取当前行的数值
    double current_px = *val_px;
    double current_py = *val_py;
    
    // 在这里进行你的物理计算，比如计算横向动量 pt
    double pt = std::sqrt(current_px * current_px + current_py * current_py);
}