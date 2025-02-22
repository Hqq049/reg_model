from typing import List, Dict
from reg_model_generator import RegModelGenerator, AccessType, SecurityType, RegModel, RegField
from pathlib import Path

class TestGenerator:
    def __init__(self, reg_model):
        self.reg_model = reg_model

    def generate_all(self, output_dir: Path):
        """生成所有测试用例"""
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        # 生成访问权限测试
        self.generate_access_test(output_dir / "apb4_reg_access_test.sv")
        # 生成其他测试用例
        # ...

    def generate_access_test(self, output_path: Path):
        """生成访问权限测试"""
        test_code = """
class apb4_reg_access_test extends uvm_test;
    `uvm_component_utils(apb4_reg_access_test)

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    virtual task run_phase(uvm_phase phase);
        // 测试逻辑
    endtask
endclass
"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(test_code)

    def generate_base_test(self, output_path: Path):
        """生成基础测试类"""
        try:
            # 确保父目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            test_code = """
class apb4_base_test extends uvm_test;
    `uvm_component_utils(apb4_base_test)
    
    // 环境实例
    apb4_env env;
    reg_block reg_model;
    
    function new(string name = "apb4_base_test", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        
        // 创建环境
        env = apb4_env::type_id::create("env", this);
        
        // 创建寄存器模型
        reg_model = reg_block::type_id::create("reg_model", this);
        reg_model.build();
        reg_model.lock_model();
        
        // 设置寄存器模型到配置数据库
        uvm_config_db#(reg_block)::set(this, "*", "reg_model", reg_model);
    endfunction
    
    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);
        
        // 连接寄存器模型和总线代理
        reg_model.default_map.set_sequencer(env.agent.sequencer, env.adapter);
        reg_model.default_map.set_auto_predict(1);
    endfunction
endclass
"""
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(test_code)
        except Exception as e:
            print(f"生成基础测试类时出错: {e}")
            raise
            
    def generate_reg_tests(self, output_path: Path):
        """生成寄存器测试用例"""
        test_code = ["""
    // 字段访问测试
    task field_access_test;
        uvm_status_e status;
        uvm_reg_data_t value;"""]
        
        # 为每个字段生成访问测试
        for reg_name, reg_model in self.reg_model.fields.items():
            for field_name, field in reg_model.fields.items():
                test_code.extend([
                    f"        // 测试 {reg_name}.{field_name}",
                    f"        reg_model.{reg_name.lower()}_{field_name}.write(status, " +
                    f"'h{(1 << field.width)-1:X});",
                    f"        reg_model.{reg_name.lower()}_{field_name}.read(status, value);"
                ])
            
        test_code.append("""
    endtask
endclass
""")
            
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(test_code))
            
    def generate_coverage(self, output_path: Path):
        """生成覆盖率收集代码"""
        try:
            if not self.reg_model.fields:
                self.reg_model.load_excel()
            
            # 确保父目录存在
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            cov_code = ["""
class apb4_reg_coverage extends uvm_subscriber #(apb4_trans);
    `uvm_component_utils(apb4_reg_coverage)
    
    reg_block reg_model;
    
    // 覆盖组定义
    covergroup reg_cg;
        option.per_instance = 1;
"""]
            
            # 为每个寄存器生成覆盖点
            for reg_name, reg_model in self.reg_model.fields.items():
                cov_code.extend([
                    f"\n        // {reg_name} 寄存器覆盖点",
                    f"        {reg_name}_cp: coverpoint reg_model.{reg_name.lower()}.get() {{",
                    f"            bins reset_value = {{{reg_model.get_reset_value()}}};",
                    f"            bins other_values[] = {{[0:{(1 << reg_model.width)-1}]}};",
                    f"        }}"
                ])
                
                # 为每个可写字段生成覆盖点
                writable_fields = [(n,f) for n,f in reg_model.fields.items() if f.is_writable()]
                if len(writable_fields) > 1:
                    cross_fields = ' , '.join([f"{n}_cp" for n,_ in writable_fields])
                    cov_code.append(f"        {reg_name}_cross: cross {cross_fields};")
                    
                for field_name, field in writable_fields:
                    cov_code.extend([
                        f"\n        // {field_name} 字段覆盖点",
                        f"        {field_name}_cp: coverpoint reg_model.{reg_name.lower()}.{field_name}.get() {{",
                        f"            bins reset = {{{field.reset_value}}};",
                        f"            bins values[] = {{[0:{(1 << field.width)-1}]}};",
                        f"            bins transitions[] = ([0:{(1 << field.width)-1}] => [0:{(1 << field.width)-1}]);",
                        f"        }}"
                    ])
                    
                    # 为特殊访问类型添加覆盖
                    if field.access_type in [AccessType.W1C.value, AccessType.W1S.value,
                                           AccessType.W0C.value, AccessType.W0S.value]:
                        cov_code.extend([
                            f"        {field_name}_access_cp: coverpoint reg_model.{reg_name.lower()}.{field_name}.get() {{",
                            f"            bins special_access = {{0,1}} iff (reg_model.{reg_name.lower()}.{field_name}.is_accessed);",
                            f"        }}"
                        ])
                        
            cov_code.extend(["""
    endgroup
    
    function new(string name, uvm_component parent);
        super.new(name, parent);
        reg_cg = new();
    endfunction
    
    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db#(reg_block)::get(this, "", "reg_model", reg_model))
            `uvm_fatal("NOREG", "No register model specified")
    endfunction
    
    virtual function void write(apb4_trans t);
        reg_cg.sample();
    endfunction
endclass
"""])
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(cov_code))
        except Exception as e:
            print(f"生成覆盖率收集代码时出错: {e}")
            raise
            
    def generate_all(self, config):
        """生成所有测试和覆盖率代码"""
        try:
            # 获取测试用例目录
            testcase_dir = config.testcase_dir
            if not testcase_dir.exists():
                testcase_dir.mkdir(parents=True)
            
            # 生成测试用例
            self.generate_base_test(testcase_dir / "apb4_base_test.sv")
            self.generate_reg_tests(testcase_dir / "apb4_reg_tests.sv")
            self.generate_coverage(testcase_dir / "apb4_coverage.sv")
            
            # 生成测试包文件
            pkg_code = """
package apb4_test_pkg;
    import uvm_pkg::*;
    import reg_model_pkg::*;
    import apb4_verif_pkg::*;
    `include "uvm_macros.svh"
    
    `include "apb4_base_test.sv"
    `include "apb4_reg_tests.sv"
    `include "apb4_coverage.sv"
endpackage
"""
            with open(testcase_dir / "apb4_test_pkg.sv", 'w') as f:
                f.write(pkg_code)
        except Exception as e:
            print(f"生成测试环境时出错: {e}")
            raise 