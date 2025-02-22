from typing import List, Dict
import pandas as pd
import os

class APB4TestGenerator:
    def __init__(self, reg_model):
        self.reg_model = reg_model
        
    def generate_access_test(self, output_path: str):
        """生成访问权限测试"""
        if self.reg_model.reg_data is None:
            self.reg_model.load_excel()
            
        reg_groups = self.reg_model.reg_data.groupby('RegisterName')
        
        test_code = ["""
class apb4_reg_access_test extends apb4_reg_base_test;
    `uvm_component_utils(apb4_reg_access_test)
    
    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        phase.raise_objection(this);
        
        // 测试每个寄存器的访问权限
"""]
        
        for reg_name, fields in reg_groups:
            test_code.append(f"""
        // 测试 {reg_name} 寄存器
        begin
            uvm_status_e status;
            uvm_reg_data_t rd_data, wr_data;""")
            
            # 为每个字段生成测试
            offset = 0
            for _, field in fields.iterrows():
                if field['RW-op'] == 'RW':
                    test_code.extend([f"""
            // 测试 {field['Filed']} 字段 (RW)
            wr_data = $urandom();
            env.reg_model.{reg_name.lower()}.{field['Filed']}.write(status, wr_data);
            env.reg_model.{reg_name.lower()}.{field['Filed']}.read(status, rd_data);
            if (rd_data != wr_data) begin
                `uvm_error("ACCESS_TEST", $sformatf("{reg_name}.{field['Filed']} write/read mismatch"))
            end"""])
                elif field['RW-op'] == 'RO':
                    test_code.extend([f"""
            // 测试 {field['Filed']} 字段 (RO)
            wr_data = $urandom();
            env.reg_model.{reg_name.lower()}.{field['Filed']}.write(status, wr_data);
            if (status == UVM_IS_OK) begin
                `uvm_error("ACCESS_TEST", $sformatf("{reg_name}.{field['Filed']} should be read-only"))
            end"""])
                offset += field['Width']
                
            test_code.append("        end\n")
            
        test_code.extend(["""
        phase.drop_objection(this);
    endtask
endclass"""])
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(test_code))
            
    def generate_concurrent_test(self, output_path: str):
        """生成并发访问测试"""
        test_code = """
class apb4_reg_concurrent_test extends apb4_reg_base_test;
    `uvm_component_utils(apb4_reg_concurrent_test)
    
    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        phase.raise_objection(this);
        
        // 并发执行多个寄存器访问
        fork
            // 随机读写任务1
            begin
                repeat(100) begin
                    uvm_reg_data_t data;
                    uvm_status_e status;
                    int reg_idx = $urandom_range(0, env.reg_model.get_registers().size()-1);
                    uvm_reg rg = env.reg_model.get_registers()[reg_idx];
                    
                    if ($urandom_range(0,1)) begin
                        data = $urandom();
                        rg.write(status, data);
                    end else begin
                        rg.read(status, data);
                    end
                end
            end
            
            // 随机读写任务2
            begin
                repeat(100) begin
                    uvm_reg_data_t data;
                    uvm_status_e status;
                    int reg_idx = $urandom_range(0, env.reg_model.get_registers().size()-1);
                    uvm_reg rg = env.reg_model.get_registers()[reg_idx];
                    
                    if ($urandom_range(0,1)) begin
                        data = $urandom();
                        rg.write(status, data);
                    end else begin
                        rg.read(status, data);
                    end
                end
            end
        join
        
        phase.drop_objection(this);
    endtask
endclass
"""
        with open(output_path, 'w') as f:
            f.write(test_code)
            
    def generate_error_test(self, output_path: str):
        """生成错误注入测试"""
        test_code = """
class apb4_reg_error_test extends apb4_reg_base_test;
    `uvm_component_utils(apb4_reg_error_test)
    
    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        phase.raise_objection(this);
        
        // 测试未对齐访问
        test_unaligned_access();
        
        // 测试无效地址访问
        test_invalid_address();
        
        // 测试写保护违规
        test_write_protect_violation();
        
        phase.drop_objection(this);
    endtask
    
    // 测试未对齐访问
    virtual task test_unaligned_access();
        uvm_status_e status;
        uvm_reg_data_t data;
        
        // 尝试在未对齐地址写入
        env.agent.write_reg_by_addr(32'h00000001, 32'hFFFFFFFF, status);
        if (status != UVM_NOT_OK) begin
            `uvm_error("ERROR_TEST", "Unaligned write should fail")
        end
        
        // 尝试在未对齐地址读取
        env.agent.read_reg_by_addr(32'h00000003, data, status);
        if (status != UVM_NOT_OK) begin
            `uvm_error("ERROR_TEST", "Unaligned read should fail")
        end
    endtask
    
    // 测试无效地址访问
    virtual task test_invalid_address();
        uvm_status_e status;
        uvm_reg_data_t data;
        
        // 尝试访问无效地址
        env.agent.write_reg_by_addr(32'hFFFFFFFF, 32'h00000000, status);
        if (status != UVM_NOT_OK) begin
            `uvm_error("ERROR_TEST", "Invalid address write should fail")
        end
        
        env.agent.read_reg_by_addr(32'hFFFFFFFF, data, status);
        if (status != UVM_NOT_OK) begin
            `uvm_error("ERROR_TEST", "Invalid address read should fail")
        end
    endtask
    
    // 测试写保护违规
    virtual task test_write_protect_violation();
        uvm_status_e status;
        uvm_reg_data_t data;
        
        // 尝试写入只读寄存器
        foreach (env.reg_model.get_registers()[i]) begin
            uvm_reg rg = env.reg_model.get_registers()[i];
            if (rg.get_rights() == "RO") begin
                data = $urandom();
                rg.write(status, data);
                if (status != UVM_NOT_OK) begin
                    `uvm_error("ERROR_TEST", $sformatf("%s is RO but write succeeded", rg.get_name()))
                end
            end
        end
    endtask
endclass
"""
        with open(output_path, 'w') as f:
            f.write(test_code)
            
    def generate_burst_test(self, output_path: str):
        """生成突发传输测试"""
        test_code = """
class apb4_reg_burst_test extends apb4_reg_base_test;
    `uvm_component_utils(apb4_reg_burst_test)
    
    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        phase.raise_objection(this);
        
        // 连续写测试
        test_consecutive_writes();
        
        // 连续读测试
        test_consecutive_reads();
        
        // 交替读写测试
        test_alternating_access();
        
        phase.drop_objection(this);
    endtask
    
    // 连续写测试
    virtual task test_consecutive_writes();
        uvm_status_e status;
        uvm_reg_data_t data;
        
        repeat(10) begin
            foreach (env.reg_model.get_registers()[i]) begin
                uvm_reg rg = env.reg_model.get_registers()[i];
                if (rg.get_rights() != "RO") begin
                    data = $urandom();
                    rg.write(status, data);
                end
            end
        end
    endtask
    
    // 连续读测试
    virtual task test_consecutive_reads();
        uvm_status_e status;
        uvm_reg_data_t data;
        
        repeat(10) begin
            foreach (env.reg_model.get_registers()[i]) begin
                uvm_reg rg = env.reg_model.get_registers()[i];
                rg.read(status, data);
            end
        end
    endtask
    
    // 交替读写测试
    virtual task test_alternating_access();
        uvm_status_e status;
        uvm_reg_data_t data;
        
        repeat(10) begin
            foreach (env.reg_model.get_registers()[i]) begin
                uvm_reg rg = env.reg_model.get_registers()[i];
                if (rg.get_rights() != "RO") begin
                    data = $urandom();
                    rg.write(status, data);
                    rg.read(status, data);
                end
            end
        end
    endtask
endclass
"""
        with open(output_path, 'w') as f:
            f.write(test_code)
            
    def generate_all_tests(self, output_dir: str):
        """生成所有测试用例"""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 生成各种测试用例
        self.generate_access_test(f"{output_dir}/apb4_reg_access_test.sv")
        self.generate_concurrent_test(f"{output_dir}/apb4_reg_concurrent_test.sv")
        self.generate_error_test(f"{output_dir}/apb4_reg_error_test.sv")
        self.generate_burst_test(f"{output_dir}/apb4_reg_burst_test.sv")
        
        # 生成测试包文件
        test_pkg_code = """
package apb4_reg_test_pkg;
    import uvm_pkg::*;
    import apb4_reg_pkg::*;
    `include "uvm_macros.svh"
    
    `include "apb4_reg_access_test.sv"
    `include "apb4_reg_concurrent_test.sv"
    `include "apb4_reg_error_test.sv"
    `include "apb4_reg_burst_test.sv"
endpackage
"""
        with open(f"{output_dir}/apb4_reg_test_pkg.sv", 'w') as f:
            f.write(test_pkg_code) 