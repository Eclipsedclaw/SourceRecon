# Translator——开发者说明

Translator 是面向既有 Geant4 Step 级 ROOT 文件的可选 ETL 工具，不依赖重建算法或 HEALPix。

## 文件职责

- `include/io_config.h`、`src/io_config.cpp`：配置路径、Tree、Branch、探测层编号和触发阈值。
- `include/root_simulation_translator.h`：对外暴露翻译入口。
- `src/root_simulation_translator.cpp`：实现按 `eventID` 分组的流式状态机、数字化聚合、触发策略和精简 ROOT 写出。
- `src/translate_main.cpp`：独立组合入口。
- `config/translator_config.json`：运行时输入输出格式映射。

输入 Tree 只遍历一次，内存消耗与单个事件的 Step 数量有关，而不是与整个文件大小有关。同一 chamber 的多个 hit 会合并成能量加权质心。程序还会检查输入和输出路径，防止 `RECREATE` 意外覆盖原始数据。

面向重建程序的事件顺序固定为：`r1/e1` 属于 ch2，`r2` 属于 ch1。

独立 Makefile 从 `../config/local.mk` 读取 ROOT、JSON 和 rpath 配置，该文件由根目录 `make configure` 一次生成。
