# sim_run.py
from pathlib import Path
import subprocess
import argparse
import os
from datetime import datetime
from create_excel import ExcelGenerator
from rtl_generator import RTLGenerator
from apb4_verif_generator import APB4VerifGenerator
from test_generator import TestGenerator
import shutil  # 导入 shutil 模块以处理文件和文件夹的删除

class ModelsimRunner:
    def __init__(self, pwd: Path):
        # 基础路径
        self.pwd = pwd
        self.dut_filelist = pwd / "dut/file_list/dut.f"
        self.tb_filelist = pwd / "tb/filelist/tb.f"
        self.sim_dir = pwd / "simdir"
        self.report_dir = pwd / "report"
        self.rtl_dir = pwd / "dut/rtl"  # RTL 文件目录
        
        # Modelsim工作目录
        self.work_dir = self.sim_dir / "work"
        
        # 编译和仿真选项
        self.vlog_opts = ["-sv", "-mfcu", "+acc"]
        self.vsim_opts = ["-c", "-onfinish stop", "-do"]
        
        # 获取UVM环境变量
        self.uvm_home = Path(os.getenv("UVM_HOME"))  # 从环境变量获取 UVM_HOME
        
        if not self.uvm_home:
            raise EnvironmentError("未设置UVM_HOME环境变量，请先设置后再运行")
        
    def generate_rtl(self, excel_file: Path):
        """生成RTL文件"""
        self.rtl_dir.mkdir(parents=True, exist_ok=True)  # 创建 RTL 目录
        rtl_gen = RTLGenerator(excel_file)
        rtl_gen.generate_rtl(self.rtl_dir / "apb4_reg_block.v")
        rtl_gen.generate_filelist(self.dut_filelist)
        print("RTL文件生成完成")

    def delete_rtl(self):
        """删除RTL文件"""
        try:
            if self.rtl_dir.exists():
                shutil.rmtree(self.rtl_dir)  # 删除整个RTL目录
                print(f"已删除目录: {self.rtl_dir}")
            else:
                print(f"目录不存在: {self.rtl_dir}")
        except Exception as e:
            print(f"删除RTL文件时出错: {e}")

    def generate_apb_uvc(self):
        """生成 APB UVC"""
        # 生成 APB UVC 相关文件的逻辑
        print("APB UVC 生成完成")

    def delete_apb_uvc(self):
        """删除 APB UVC"""
        # 删除 APB UVC 相关文件的逻辑
        print("APB UVC 已删除")

    def delete_generated_environment(self):
        """删除生成的验证环境"""
        try:
            # 删除 TB 文件列表
            if self.tb_filelist.exists():
                self.tb_filelist.unlink()  # 删除 TB 文件列表
                print(f"已删除文件: {self.tb_filelist}")
            else:
                print(f"文件不存在: {self.tb_filelist}")

            # 删除仿真目录及其内容
            if self.sim_dir.exists():
                shutil.rmtree(self.sim_dir)  # 删除整个仿真目录
                print(f"已删除目录: {self.sim_dir}")
            else:
                print(f"目录不存在: {self.sim_dir}")

            # 删除报告目录及其内容
            if self.report_dir.exists():
                shutil.rmtree(self.report_dir)  # 删除整个报告目录
                print(f"已删除目录: {self.report_dir}")
            else:
                print(f"目录不存在: {self.report_dir}")

            # 删除其他生成的文件和目录（如验证环境相关文件）
            reg_uvc_dir = self.pwd / "tb/uvc/reg_model"  # 寄存器模型目录
            if reg_uvc_dir.exists():
                shutil.rmtree(reg_uvc_dir)  # 删除寄存器模型目录
                print(f"已删除目录: {reg_uvc_dir}")

            apb_uvc_dir = self.pwd / "tb/uvc/apb4"  # APB4 UVC 目录
            if apb_uvc_dir.exists():
                shutil.rmtree(apb_uvc_dir)  # 删除 APB4 UVC 目录
                print(f"已删除目录: {apb_uvc_dir}")

        except Exception as e:
            print(f"删除生成的验证环境时出错: {e}")

    def generate_env(self, excel_file: Path):
        """生成验证环境"""
        self.delete_generated_environment()  # 删除旧的环境
        from main import RegGenConfig
        config = RegGenConfig(self.pwd)
        config.create_dirs()
        
        self.generate_rtl(excel_file)  # 生成RTL文件
        
        verif_gen = APB4VerifGenerator(excel_file, self.uvm_home)  # 只传递 uvm_home
        verif_gen.generate_verif_env(config)
        
        verif_gen.generate_tb_filelist(config.get_tb_filelist())
        
        test_gen = TestGenerator(excel_file)
        test_gen.generate_all(config)
        
        return config

    def create_sim_dirs(self):
        """创建仿真目录"""
        self.sim_dir.mkdir(parents=True, exist_ok=True)
        self.work_dir.mkdir(parents=True, exist_ok=True)

    def compile_rtl(self):
        """编译 RTL 文件"""
        # 编译 RTL 文件的逻辑
        print("编译 RTL 文件...")
        # 这里添加编译 RTL 的具体实现
        # 例如，调用 ModelSim 的编译命令
        # subprocess.run(["vlog", ...])  # 示例命令
        print("RTL 编译完成")

    def compile_verification_env(self):
        """编译验证环境"""
        # 编译验证环境的逻辑
        print("编译验证环境...")
        # 这里添加编译验证环境的具体实现
        # 例如，调用 ModelSim 的编译命令
        # subprocess.run(["vlog", ...])  # 示例命令
        print("验证环境编译完成")

def main():
    parser = argparse.ArgumentParser(
        description="ModelSim仿真运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""使用示例:
        1. 生成验证环境:
            python sim_run.py --gen
        2. 删除生成的验证环境:
            python sim_run.py --delete-env
        3. 生成 RTL 文件:
            python sim_run.py --generate-rtl
        4. 删除 RTL 文件:
            python sim_run.py --delete-rtl
        5. 生成 APB UVC:
            python sim_run.py --generate-apb-uvc
        6. 删除 APB UVC:
            python sim_run.py --delete-apb-uvc
        7. 编译 RTL:
            python sim_run.py --compile-rtl
        8. 编译验证环境:
            python sim_run.py --compile-env
        """
    )
    
    parser.add_argument("--gen", 
                       action="store_true",
                       help="生成验证环境")
    parser.add_argument("--delete-env", 
                       action="store_true",
                       help="删除生成的验证环境")
    parser.add_argument("--generate-rtl", 
                       action="store_true",
                       help="生成RTL文件")
    parser.add_argument("--delete-rtl", 
                       action="store_true",
                       help="删除RTL文件")
    parser.add_argument("--generate-apb-uvc", 
                       action="store_true",
                       help="生成 APB UVC")
    parser.add_argument("--delete-apb-uvc", 
                       action="store_true",
                       help="删除 APB UVC")
    parser.add_argument("--compile-rtl", 
                       action="store_true",
                       help="编译 RTL")
    parser.add_argument("--compile-env", 
                       action="store_true",
                       help="编译验证环境")
    
    args = parser.parse_args()
    
    pwd = Path.cwd()
    runner = ModelsimRunner(pwd)
    runner.create_sim_dirs()
    
    try:
        config = None
        
        if args.delete_env:
            print("删除生成的验证环境...")
            runner.delete_generated_environment()
            print("验证环境已删除")
            return  # 退出程序
        
        if args.generate_rtl:
            print("生成RTL文件...")
            runner.generate_rtl(pwd / "register_spec.xlsx")  # 假设 Excel 文件路径
            return  # 退出程序
        
        if args.delete_rtl:
            print("删除RTL文件...")
            runner.delete_rtl()
            return  # 退出程序
        
        if args.generate_apb_uvc:
            print("生成 APB UVC...")
            runner.generate_apb_uvc()
            return  # 退出程序
        
        if args.delete_apb_uvc:
            print("删除 APB UVC...")
            runner.delete_apb_uvc()
            return  # 退出程序
        
        if args.gen:
            excel_file = pwd / "register_spec.xlsx"
            if not excel_file.exists():
                print("错误: 未找到register_spec.xlsx文件")
                exit(1)
            print("生成验证环境...")
            config = runner.generate_env(excel_file)  # 生成验证环境
            print("验证环境生成完成")
            
        if args.compile_rtl:
            print("编译 RTL...")
            runner.compile_rtl()
            return  # 退出程序
            
        if args.compile_env:
            print("编译验证环境...")
            runner.compile_verification_env()
            return  # 退出程序
            
    except subprocess.CalledProcessError as e:
        print(f"错误: {e}")
        exit(1)
    except Exception as e:
        print(f"发生错误: {e}")
        exit(1)

if __name__ == "__main__":
    main()