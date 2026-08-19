### 综合实战挑战：双粒子衰变的共振峰重建与高斯拟合（`Challenge_ResonanceFit.cc`）

恭喜你学完 Step 1 到 Step 3！这里为你设计了一道综合练习题，把 **TTree 生成、TTreeReader 读取、不变质量重构、直方图填充、TF1 拟合与状态检查** 全部串联起来。

---

**任务背景（物理场景）**

某个不稳定共振态粒子 $X$ 发生两体衰变：$X \to a + b$。

* 衰变产物 $a$ 和 $b$ 在探测器中测得的能量分别为 $E_a, E_b$，沿束流方向的动量分量分别为 $p_{za}, p_{zb}$。
* 理论上，$X$ 粒子的静止质量（不变质量 $M$）满足：

$$M = \sqrt{(E_a + E_b)^2 - (p_{za} + p_{zb})^2}$$


* 在实验中，由于物理共振峰和探测器能量分辨率效应，$M$ 的测量值在真实质量 $M_0 = 3.10\text{ GeV}$ 附近呈高斯展宽，标准差 $\sigma \approx 0.05\text{ GeV}$。

---

**编程目标**

请编写一个完整的 ROOT C++ 宏（例如命名为 `Challenge_ResonanceFit.cc`），分为两个独立或串联的函数：

#### 阶段 1：模拟生成数据并写入文件（Write Phase）

1. 创建 ROOT 文件 `resonance_data.root`（使用 `std::unique_ptr<TFile>` 管理）。
2. 创建一棵名为 `"DecayTree"` 的 `TTree`。
3. 建立 4 个分支（Branch）：`Ea`, `Eb`, `pza`, `pzb`（均为 `double` 类型）。
4. 循环生成 **10000** 个事件：
* 用 `TRandom3`（或 C++ `<random>`）生成服从高斯分布 $M \sim \mathcal{N}(3.10, 0.05^2)$ 的不变质量 $M$。
* 设定简化运动学：令总动量 $P_z = p_{za} + p_{zb} \sim \mathcal{N}(0.0, 1.0^2)$。
* 则总能量 $E_{\text{tot}} = \sqrt{M^2 + P_z^2}$。
* 随机平分或按比例分配给两个粒子（如 $E_a = 0.5 \cdot E_{\text{tot}}$, $E_b = E_{\text{tot}} - E_a$；$p_{za} = 0.5 \cdot P_z$, $p_{zb} = P_z - p_{za}$）。


5. 填充并写入 `TTree`，最后安全保存文件。

#### 阶段 2：读取分析、画图与高斯拟合（Read & Fit Phase）

1. 使用 RAII 风格打开 `resonance_data.root` 并获取 `"DecayTree"`。
2. 使用 **`TTreeReader`** 和 **`TTreeReaderValue<double>`** 安全读取 4 个分支的数据。
3. 在栈上或用 `std::make_unique` 创建一个 `TH1D` 直方图：
* 命名为 `"h_mass"`，标题设为 `"Invariant Mass Reconstruction;M_{inv} [GeV];Events / (0.02 GeV)"`。
* Bin 划分：范围设为 `[2.5, 3.7]`，共 `60` 个 bin。


4. 遍历所有事件，计算每个事件的不变质量 $M_{\text{inv}} = \sqrt{(E_a + E_b)^2 - (p_{za} + p_{zb})^2}$ 并填入直方图。
5. **构建拟合**：
* 在栈上创建一个 `TF1` 高斯拟合函数（使用预设代号 `"gaus"`），拟合区间设为 `[2.9, 3.3]`。
* 提取直方图统计量（`GetMaximum()`, `GetMean()`, `GetStdDev()`）为高斯函数的 3 个参数设置合理的初始猜测值。


6. **执行拟合与安全验证**：
* 在新建的 `TCanvas` 上先绘制带误差棒的直方图（`"E"`）。
* 调用 `Fit()` 拟合，使用 `"S"` 选项保存结果到 `TFitResultPtr`。
* 使用 `static_cast<int>` 显式检查拟合状态码，若非 0 输出错误告警。


7. 在终端打印出拟合得到的共振峰中心值（Mean）**和**展宽（Sigma）以及对应的拟合误差。
8. 将最终带有拟合红线和统计框的画布保存为 `resonance_fit.png`。

---

你可以先自己上手写一版，遇到任何语法、编译报错或 ROOT 机制问题随时发出来，我们一起来 Review 和优化！