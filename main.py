import os
from pathlib import Path
from create_excel import ExcelGenerator
from rtl_generator import RTLGenerator
from apb4_verif_generator import APB4VerifGenerator
from test_generator import TestGenerator
from report_generator import ReportGenerator

class RegGenConfig:
    """生成器配置类"""
    def __init__(self, pwd: Path):
        # DUT相关路径
        self.dut_root = pwd / "dut"
        self.rtl_dir = self.dut_root / "rtl"
        self.dut_filelist = self.dut_root / "file_list"
        
        # TB相关路径
        self.tb_root = pwd / "tb"
        
        # UVC组件路径
        self.uvc_root = self.tb_root / "uvc"
        self.reg_uvc_dir = self.uvc_root / "reg_model"  # 寄存器模型UVC
        self.apb_uvc_dir = self.uvc_root / "apb4"       # APB4 UVC
        
        self.env_dir = self.tb_root / "env"
        self.filelist_dir = self.tb_root / "filelist"
        
        # 测试相关路径
        self.benchmark_dir = self.tb_root / "benchmark"
        self.sequence_dir = self.benchmark_dir / "sequence"
        self.testcase_dir = self.benchmark_dir / "testcase"
        self.tc_lib_dir = self.benchmark_dir / "tc_include_lib"
        
        # 仿真和报告路径(移到顶层)
        self.sim_dir = pwd / "simdir"
        self.report_dir = pwd / "report"
        
    def create_dirs(self):
        """创建所有必要的目录"""
        dirs = [
            self.rtl_dir,
            self.dut_filelist,
            self.uvc_root,
            self.env_dir, 
            self.filelist_dir,
            self.sequence_dir,
            self.testcase_dir,
            self.tc_lib_dir,
            self.sim_dir,
            self.report_dir
        ]
        for dir in dirs:
            dir.mkdir(parents=True, exist_ok=True)
            
    def get_dut_filelist(self) -> Path:
        """获取DUT文件列表路径"""
        return self.dut_filelist / "dut.f"
        
    def get_tb_filelist(self) -> Path:
        """获取TB文件列表路径"""
        return self.filelist_dir / "tb.f"

def print_dir_structure(config: RegGenConfig):
    """打印目录结构"""
    print("\n生成目录结构:")
    print(".")
    print("├── register_spec.xlsx")
    print("├── simdir")
    print("│   └── (仿真文件)")
    print("├── report")
    print("│   ├── register_report.docx")
    print("│   └── coverage_report.html")
    print("├── dut")
    print("│   ├── rtl")
    print("│   │   └── apb4_reg_block.v")
    print("│   └── file_list")
    print("│       └── dut.f")
    print("└── tb")
    print("    ├── uvc")
    print("    │   ├── reg_model")
    print("    │   │   ├── reg_model_pkg.sv")
    print("    │   │   ├── reg_block.sv")
    print("    │   │   └── reg_adapter.sv")
    print("    │   └── apb4")
    print("    │       ├── apb4_pkg.sv")
    print("    │       ├── apb4_if.sv")
    print("    │       ├── apb4_types.sv")
    print("    │       ├── apb4_config.sv")
    print("    │       ├── apb4_driver.sv")
    print("    │       ├── apb4_monitor.sv")
    print("    │       ├── apb4_sequencer.sv")
    print("    │       └── apb4_agent.sv")
    print("    ├── env")
    print("    │   ├── apb4_env.sv")
    print("    │   ├── test_top.sv")
    print("    │   └── tb.sv")
    print("    ├── filelist")
    print("    │   └── tb.f")
    print("    └── benchmark")
    print("        ├── sequence")
    print("        │   ├── apb4_base_sequence.sv")
    print("        │   └── apb4_reg_sequences.sv")
    print("        ├── testcase")
    print("        │   ├── apb4_base_test.sv")
    print("        │   └── apb4_reg_tests.sv")
    print("        └── tc_include_lib")
    print("            └── apb4_test_pkg.sv")
    print("\n")

def main():
    pwd = Path.cwd()
    config = RegGenConfig(pwd)
    config.create_dirs()
    
    # 打印目录结构
    print_dir_structure(config)
    
    # 1. 创建Excel模板（如果不存在）
    excel_gen = ExcelGenerator()
    excel_file = pwd / "register_spec.xlsx"
    if not excel_file.exists():
        excel_gen.create_template(excel_file)
        print(f"已创建寄存器定义模板: {excel_file}")
        print("请填写寄存器定义后再次运行此脚本")
        return
        
    # 2. 生成RTL代码
    rtl_gen = RTLGenerator(excel_file)
    rtl_gen.generate_rtl(config.rtl_dir / "apb4_reg_block.v")
    rtl_gen.generate_filelist(config.get_dut_filelist())
    
    # 3. 生成验证环境
    verif_gen = APB4VerifGenerator(excel_file)
    verif_gen.generate_verif_env(config)  # 传入配置对象
    
    # 4. 生成测试用例和覆盖率
    test_gen = TestGenerator(excel_file)
    test_gen.generate_all(config)  # 传入配置对象
    
    # 5. 生成报告
    report_gen = ReportGenerator(excel_file)
    report_gen.generate_report(config.report_dir / "register_report.docx")
    
    print("生成完成！")
    print(f"RTL代码位置: {config.rtl_dir}")
    print(f"验证环境位置: {config.tb_root}")
    print(f"测试用例位置: {config.benchmark_dir}")
    print(f"报告输出位置: {config.report_dir}")

if __name__ == "__main__":
    main() 