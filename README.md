# APB4 寄存器模型生成器

这是一个基于 UVM 的 APB4 寄存器模型生成和验证工具。它可以从 Excel 规格表自动生成 RTL 代码、UVM 验证环境和测试用例。

## 功能特点

- 从 Excel 生成 RTL 寄存器模块
- 生成完整的 UVM 验证环境
- 支持多种寄存器访问类型 (RW, RO, WO, W1C, W1S, RC, RS 等)
- 自动生成测试用例和覆盖率收集
- 支持回归测试和测试报告生成

## 目录结构

```
./
├── register_spec.xlsx    # 寄存器规格表
├── dut/                  # 设计文件目录
│   ├── rtl/             # RTL设计文件
│   └── file_list/       # DUT文件列表
├── tb/                   # 测试平台目录
│   ├── uvc/             # 验证组件
│   │   ├── reg_model/   # 寄存器模型
│   │   └── apb4/        # APB4 UVC
│   ├── env/             # 验证环境
│   ├── filelist/        # TB文件列表
│   └── benchmark/       # 测试用例
│       ├── sequence/    # 测试序列
│       ├── testcase/    # 测试用例
│       └── tc_include_lib/ # 测试库文件
├── simdir/              # 仿真工作目录
│   ├── work/           # ModelSim工作库
│   ├── *.log          # 仿真日志
│   └── *.do           # ModelSim命令文件
└── report/             # 测试报告目录
    ├── regression_report.txt    # 回归测试报告
    └── *_coverage.ucdb         # 覆盖率数据
```

## 环境要求

- Python 3.6+
- ModelSim/QuestaSim
- UVM 1.2

## 环境变量设置

在运行前需要设置以下环境变量：

```bash
# Windows CMD
set UVM_HOME=D:\Program Files\modeltech64_2020.4\verilog_src\uvm-1.2


# Windows PowerShell
$env:UVM_HOME = "D:\Program Files\modeltech64_2020.4\verilog_src\uvm-1.2"
```

## 使用方法

1. 生成验证环境：
   ```bash
   python sim_run.py --gen
   ```

2. 删除生成的验证环境：
   ```bash
   python sim_run.py --delete-env
   ```

3. 生成 RTL 文件：
   ```bash
   python sim_run.py --generate-rtl
   ```

4. 删除 RTL 文件：
   ```bash
   python sim_run.py --delete-rtl
   ```

5. 编译设计文件：
   ```bash
   python sim_run.py --compile
   ```

6. 运行测试：
   ```bash
   python sim_run.py --test apb4_reg_test
   ```

7. GUI模式运行：
   ```bash
   python sim_run.py --test apb4_reg_test --gui
   ```

8. 运行回归测试：
   ```bash
   python sim_run.py --regression
   ```

9. 一键执行全部（生成 + 编译 + 运行）：
   ```bash
   python sim_run.py --gen --compile --test apb4_reg_test
   ```

## 命令行参数

- `--gen`: 生成验证环境
- `--delete-env`: 删除生成的验证环境
- `--generate-rtl`: 生成 RTL 文件
- `--delete-rtl`: 删除 RTL 文件
- `--compile`: 编译设计文件
- `--test TEST`: 指定要运行的测试名称（例如: apb4_reg_test）
- `--gui`: 使用 GUI 模式运行 ModelSim
- `--regression`: 运行回归测试
- `--pattern PATTERN`: 回归测试的测试用例匹配模式（默认: apb4_*_test）

## 注意事项

1. 运行前请确保已正确设置 UVM_HOME 和 UVM_DPI_HOME 环境变量
2. 首次运行需要先生成验证环境 (--gen)
3. 修改代码后需要重新编译 (--compile)
4. 建议使用绝对路径设置环境变量

## 常见问题

1. UVM DPI库未找到：
   - 检查 UVM_DPI_HOME 环境变量设置
   - 确认 uvm_dpi.dll 文件存在

2. 编译错误：
   - 确保已安装正确版本的 ModelSim/QuestaSim
   - 检查文件列表路径是否正确

3. 运行测试失败：
   - 检查是否已完成编译
   - 查看仿真日志获取详细错误信息