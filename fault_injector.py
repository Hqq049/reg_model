from typing import List, Dict
from pathlib import Path
import random

class FaultInjector:
    def __init__(self, reg_model):
        self.reg_model = reg_model
        
    def generate_fault_sequence(self, output_path: Path):
        """生成错误注入序列"""
        try:
            fault_code = ["""
class apb4_fault_sequence extends apb4_base_sequence;
    `uvm_object_utils(apb4_fault_sequence)
    
    function new(string name = "apb4_fault_sequence");
        super.new(name);
    endfunction
    
    virtual task body();
        apb4_trans trans;
        uvm_status_e status;
        uvm_reg_data_t value;
        
        // 1. 地址错误注入
        trans = apb4_trans::type_id::create("trans");
        start_item(trans);
        trans.paddr = 32'hFFFF_FFFF;  // 无效地址
        trans.pwrite = 1'b0;
        trans.pstrb = 4'hF;
        finish_item(trans);
        
        // 2. 字节写使能错误注入
        trans = apb4_trans::type_id::create("trans");
        start_item(trans);
        trans.paddr = 32'h0000_0000;
        trans.pwrite = 1'b1;
        trans.pstrb = 4'h5;  // 无效的字节使能
        finish_item(trans);
"""]

            # 3. 安全访问错误注入
            for reg_name, reg_model in self.reg_model.reg_models.items():
                if reg_model.is_secure():
                    fault_code.extend([
                        f"\n        // 对安全寄存器 {reg_name} 进行非安全访问",
                        f"        trans = apb4_trans::type_id::create(\"trans\");",
                        f"        start_item(trans);",
                        f"        trans.paddr = {reg_name}_ADDR;",
                        f"        trans.pwrite = 1'b1;",
                        f"        trans.pwdata = 32'hFFFF_FFFF;",
                        f"        trans.secure = 1'b0;  // 非安全访问",
                        f"        finish_item(trans);"
                    ])

            # 4. 读写权限错误注入
            for reg_name, reg_model in self.reg_model.reg_models.items():
                for field_name, field in reg_model.fields.items():
                    if not field.is_writable():
                        fault_code.extend([
                            f"\n        // 尝试写入只读字段 {reg_name}.{field_name}",
                            f"        trans = apb4_trans::type_id::create(\"trans\");",
                            f"        start_item(trans);",
                            f"        trans.paddr = {reg_name}_ADDR;",
                            f"        trans.pwrite = 1'b1;",
                            f"        trans.pwdata = (32'h1 << {field.offset});",
                            f"        trans.pstrb = (4'h1 << {field.offset//8});",
                            f"        finish_item(trans);"
                        ])

            # 5. 并发访问错误注入
            fault_code.extend(["""
        // 并发访问测试
        fork
            begin
                trans = apb4_trans::type_id::create("trans1");
                start_item(trans);
                trans.paddr = 32'h0000_0000;
                trans.pwrite = 1'b1;
                finish_item(trans);
            end
            begin
                trans = apb4_trans::type_id::create("trans2");
                start_item(trans);
                trans.paddr = 32'h0000_0000;
                trans.pwrite = 1'b0;
                finish_item(trans);
            end
        join_none
        
        #100;  // 等待一段时间
        
        // 6. 复位期间访问
        trans = apb4_trans::type_id::create("trans");
        start_item(trans);
        trans.paddr = 32'h0000_0000;
        trans.pwrite = 1'b1;
        trans.during_reset = 1'b1;  // 复位期间访问标志
        finish_item(trans);
    endtask
endclass

// 错误注入测试类
class apb4_fault_test extends apb4_base_test;
    `uvm_component_utils(apb4_fault_test)
    
    function new(string name = "apb4_fault_test", uvm_component parent = null);
        super.new(name, parent);
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        apb4_fault_sequence seq;
        
        phase.raise_objection(this);
        
        seq = apb4_fault_sequence::type_id::create("seq");
        seq.start(env.agent.sequencer);
        
        phase.drop_objection(this);
    endtask
    
    // 错误检查器
    virtual function void check_phase(uvm_phase phase);
        // 检查错误响应
        if(env.agent.monitor.error_count == 0)
            `uvm_error(get_type_name(), "No errors detected during fault injection")
            
        // 检查寄存器状态
        foreach(reg_model.registers[reg_name]) begin
            if(!reg_model.registers[reg_name].is_valid())
                `uvm_error(get_type_name(), $sformatf("Register %s corrupted", reg_name))
        end
    endfunction
endclass
"""])

            # 写入文件
            with open(output_path, 'w') as f:
                f.write('\n'.join(fault_code))
            
        except Exception as e:
            print(f"生成错误注入代码时出错: {e}")
            raise 