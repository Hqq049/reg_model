from typing import List, Dict
from reg_model_generator import RegModelGenerator, AccessType, SecurityType, RegModel, RegField

class TestGenerator:
    def __init__(self, excel_file: str):
        self.reg_model_gen = RegModelGenerator(excel_file)
        
    def generate_base_test(self, output_path: str):
        """生成基础测试类"""
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
        with open(output_path, 'w') as f:
            f.write(test_code)
            
    def generate_reg_tests(self, output_path: str):
        """生成寄存器测试用例"""
        if not self.reg_model_gen.reg_models:
            self.reg_model_gen.load_excel()
            
        test_code = ["""
// 寄存器复位测试
class apb4_reg_reset_test extends apb4_base_test;
    `uvm_component_utils(apb4_reg_reset_test)
    
    function new(string name = "apb4_reg_reset_test", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        uvm_status_e status;
        uvm_reg_data_t value;
        
        phase.raise_objection(this);
        
        // 检查每个寄存器的复位值"""]
        
        # 为每个寄存器生成复位值检查
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            test_code.extend([
                f"\n        // 检查 {reg_name} 寄存器复位值",
                f"        reg_model.{reg_name.lower()}.read(status, value);",
                f"        if (value != {reg_model.get_reset_value()}) begin",
                f"            `uvm_error(get_type_name(), ",
                f"                $sformatf(\"{reg_name} reset value mismatch, exp: %0h, got: %0h\",",
                f"                {reg_model.get_reset_value()}, value))",
                f"        end"
            ])
            
        test_code.extend(["""
        phase.drop_objection(this);
    endtask
endclass

// 寄存器访问测试
class apb4_reg_access_test extends apb4_base_test;
    `uvm_component_utils(apb4_reg_access_test)
    
    function new(string name = "apb4_reg_access_test", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        uvm_status_e status;
        uvm_reg_data_t value;
        
        phase.raise_objection(this);
"""])
        
        # 为每个寄存器生成访问测试
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            test_code.extend([
                f"\n        // 测试 {reg_name} 寄存器访问"
            ])
            
            # 为每个字段生成测试
            for field_name, field in reg_model.fields.items():
                if field.is_writable():
                    test_code.extend([
                        f"        // 测试 {field_name} 字段 ({field.access_type})",
                        f"        reg_model.{reg_name.lower()}.{field_name}.write(status, 'h{(1 << field.width)-1:X});",
                        f"        reg_model.{reg_name.lower()}.{field_name}.read(status, value);",
                        f"        if (value != 'h{(1 << field.width)-1:X}) begin",
                        f"            `uvm_error(get_type_name(), ",
                        f"                $sformatf(\"{reg_name}.{field_name} write/read mismatch\"))",
                        f"        end"
                    ])
                    
        test_code.extend(["""
        phase.drop_objection(this);
    endtask
endclass

// 寄存器安全访问测试
class apb4_reg_secure_test extends apb4_base_test;
    `uvm_component_utils(apb4_reg_secure_test)
    
    function new(string name = "apb4_reg_secure_test", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        uvm_status_e status;
        uvm_reg_data_t value;
        
        phase.raise_objection(this);
"""])
        
        # 为每个安全寄存器生成测试
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            if reg_model.is_secure():
                test_code.extend([
                    f"\n        // 测试 {reg_name} 安全访问",
                    f"        reg_model.{reg_name.lower()}.write(status, 'h{(1 << reg_model.width)-1:X}, .secure(0));",
                    f"        if (status != UVM_NOT_OK) begin",
                    f"            `uvm_error(get_type_name(), ",
                    f"                $sformatf(\"{reg_name} non-secure write should fail\"))",
                    f"        end"
                ])
                
        test_code.extend(["""
        phase.drop_objection(this);
    endtask
endclass
"""])
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(test_code))
            
    def generate_coverage(self, output_path: str):
        """生成覆盖率收集代码"""
        if not self.reg_model_gen.reg_models:
            self.reg_model_gen.load_excel()
            
        cov_code = ["""
class apb4_reg_coverage extends uvm_subscriber #(apb4_trans);
    `uvm_component_utils(apb4_reg_coverage)
    
    reg_block reg_model;
    
    // 覆盖组定义
    covergroup reg_cg;
        option.per_instance = 1;
"""]
        
        # 为每个寄存器生成覆盖点
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
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
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(cov_code))
            
    def generate_all(self, output_dir: str):
        """生成所有测试和覆盖率代码"""
        import os
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 生成测试用例
        self.generate_base_test(f"{output_dir}/apb4_base_test.sv")
        self.generate_reg_tests(f"{output_dir}/apb4_reg_tests.sv")
        self.generate_coverage(f"{output_dir}/apb4_coverage.sv")
        
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
        with open(f"{output_dir}/apb4_test_pkg.sv", 'w') as f:
            f.write(pkg_code) 