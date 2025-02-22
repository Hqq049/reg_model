from typing import List, Dict
import pandas as pd
from reg_model_generator import RegModelGenerator, AccessType, SecurityType, RegModel, RegField

class APB4VerifGenerator:
    def __init__(self, excel_file: str):
        self.reg_model_gen = RegModelGenerator(excel_file)
        
    def generate_interface(self, output_path: str):
        """生成APB4接口定义"""
        interface_code = """
interface apb4_if (input bit pclk);
    logic        presetn;
    logic        psel;
    logic        penable;
    logic [31:0] paddr;
    logic        pwrite;
    logic [31:0] pwdata;
    logic [3:0]  pstrb;
    logic        pready;
    logic        pslverr;
    logic [31:0] prdata;
    
    // APB4主机端口
    modport master (
        output psel, penable, paddr, pwrite, pwdata, pstrb,
        input  pready, pslverr, prdata,
        input  pclk, presetn
    );
    
    // APB4从机端口
    modport slave (
        input  psel, penable, paddr, pwrite, pwdata, pstrb,
        output pready, pslverr, prdata,
        input  pclk, presetn
    );
    
    // 监控端口
    clocking monitor_cb @(posedge pclk);
        default input #1step;
        input psel, penable, paddr, pwrite, pwdata, pstrb;
        input pready, pslverr, prdata;
    endclocking
    
    modport monitor (clocking monitor_cb);
endinterface
"""
        with open(output_path, 'w') as f:
            f.write(interface_code)
            
    def generate_transaction(self, output_path: str):
        """生成APB4事务类"""
        trans_code = """
class apb4_trans extends uvm_sequence_item;
    `uvm_object_utils(apb4_trans)
    
    // 事务属性
    rand bit [31:0] paddr;
    rand bit        pwrite;
    rand bit [31:0] pwdata;
    rand bit [3:0]  pstrb;
    bit [31:0]      prdata;
    bit             pslverr;
    rand bit        secure;  // 安全属性
    
    // 约束
    constraint c_addr_align {
        paddr[1:0] == 2'b00;  // 4字节对齐
    }
    
    constraint c_strb_valid {
        if (pwrite) {
            pstrb inside {4'b0001, 4'b0010, 4'b0100, 4'b1000,  // 单字节
                         4'b0011, 4'b1100,                      // 半字
                         4'b1111};                              // 全字
        } else {
            pstrb == 4'b1111;  // 读操作总是全字
        }
    }
    
    function new(string name = "apb4_trans");
        super.new(name);
    endfunction
    
    function string convert2string();
        return $sformatf("addr=0x%0h write=%0b data=0x%0h strb=0x%0h error=%0b secure=%0b",
                        paddr, pwrite, pwrite ? pwdata : prdata, pstrb, pslverr, secure);
    endfunction
endclass
"""
        with open(output_path, 'w') as f:
            f.write(trans_code)
            
    def generate_driver(self, output_path: str):
        """生成APB4驱动器"""
        driver_code = """
class apb4_driver extends uvm_driver #(apb4_trans);
    `uvm_component_utils(apb4_driver)
    
    virtual apb4_if vif;
    
    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction
    
    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db#(virtual apb4_if)::get(this, "", "vif", vif))
            `uvm_fatal("NOVIF", "No virtual interface specified")
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        // 初始化信号
        vif.psel <= 0;
        vif.penable <= 0;
        vif.paddr <= 0;
        vif.pwrite <= 0;
        vif.pwdata <= 0;
        vif.pstrb <= 0;
        
        forever begin
            seq_item_port.get_next_item(req);
            
            // 设置地址阶段
            @(posedge vif.pclk);
            vif.psel <= 1;
            vif.penable <= 0;
            vif.paddr <= req.paddr;
            vif.pwrite <= req.pwrite;
            vif.pwdata <= req.pwdata;
            vif.pstrb <= req.pstrb;
            
            // 设置使能阶段
            @(posedge vif.pclk);
            vif.penable <= 1;
            
            // 等待从机响应
            do begin
                @(posedge vif.pclk);
            end while (!vif.pready);
            
            // 采集响应
            if (!req.pwrite) begin
                req.prdata = vif.prdata;
            end
            req.pslverr = vif.pslverr;
            
            // 复位信号
            vif.psel <= 0;
            vif.penable <= 0;
            
            seq_item_port.item_done();
        end
    endtask
endclass
"""
        with open(output_path, 'w') as f:
            f.write(driver_code)
            
    def generate_monitor(self, output_path: str):
        """生成APB4监视器"""
        monitor_code = """
class apb4_monitor extends uvm_monitor;
    `uvm_component_utils(apb4_monitor)
    
    virtual apb4_if vif;
    uvm_analysis_port #(apb4_trans) ap;
    
    function new(string name, uvm_component parent);
        super.new(name, parent);
        ap = new("ap", this);
    endfunction
    
    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        if (!uvm_config_db#(virtual apb4_if)::get(this, "", "vif", vif))
            `uvm_fatal("NOVIF", "No virtual interface specified")
    endfunction
    
    virtual task run_phase(uvm_phase phase);
        forever begin
            apb4_trans trans;
            
            // 等待传输开始
            @(posedge vif.pclk iff vif.psel);
            
            trans = apb4_trans::type_id::create("trans");
            trans.paddr = vif.paddr;
            trans.pwrite = vif.pwrite;
            trans.pwdata = vif.pwdata;
            trans.pstrb = vif.pstrb;
            
            // 等待传输完成
            do begin
                @(posedge vif.pclk);
            end while (!vif.pready);
            
            trans.prdata = vif.prdata;
            trans.pslverr = vif.pslverr;
            
            ap.write(trans);
        end
    endtask
endclass
"""
        with open(output_path, 'w') as f:
            f.write(monitor_code)
            
    def generate_agent(self, output_path: str):
        """生成APB4代理"""
        agent_code = """
class apb4_agent extends uvm_agent;
    `uvm_component_utils(apb4_agent)
    
    apb4_driver    driver;
    apb4_monitor   monitor;
    uvm_sequencer #(apb4_trans) sequencer;
    
    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction
    
    function void build_phase(uvm_phase phase);
        super.build_phase(phase);
        
        monitor = apb4_monitor::type_id::create("monitor", this);
        
        if (get_is_active() == UVM_ACTIVE) begin
            driver = apb4_driver::type_id::create("driver", this);
            sequencer = uvm_sequencer#(apb4_trans)::type_id::create("sequencer", this);
        end
    endfunction
    
    function void connect_phase(uvm_phase phase);
        if (get_is_active() == UVM_ACTIVE) begin
            driver.seq_item_port.connect(sequencer.seq_item_export);
        end
    endfunction
endclass
"""
        with open(output_path, 'w') as f:
            f.write(agent_code)
            
    def generate_sequences(self, output_path: str):
        """生成APB4序列"""
        if not self.reg_model_gen.reg_models:
            self.reg_model_gen.load_excel()
            
        seq_code = ["""
class apb4_base_sequence extends uvm_sequence #(apb4_trans);
    `uvm_object_utils(apb4_base_sequence)
    
    function new(string name = "apb4_base_sequence");
        super.new(name);
    endfunction
endclass

class apb4_reg_sequence extends apb4_base_sequence;
    `uvm_object_utils(apb4_reg_sequence)
    
    function new(string name = "apb4_reg_sequence");
        super.new(name);
    endfunction
    
    virtual task body();
        apb4_trans trans;
"""]
        
        # 为每个寄存器生成访问序列
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            seq_code.extend([
                f"\n        // 访问 {reg_name} 寄存器",
                f"        trans = apb4_trans::type_id::create(\"trans\");",
                f"        start_item(trans);",
                f"        trans.paddr = {reg_name}_ADDR;",
                f"        trans.pwrite = 0;  // 读取复位值",
                f"        trans.pstrb = 4'hF;",
                f"        trans.secure = {1 if reg_model.is_secure() else 0};",
                f"        finish_item(trans);\n"
            ])
            
            # 为可写字段生成写访问
            for field_name, field in reg_model.fields.items():
                if field.is_writable():
                    seq_code.extend([
                        f"        // 写入 {reg_name}.{field_name}",
                        f"        trans = apb4_trans::type_id::create(\"trans\");",
                        f"        start_item(trans);",
                        f"        trans.paddr = {reg_name}_ADDR;",
                        f"        trans.pwrite = 1;",
                        f"        trans.pwdata = 32'h{1 << field.offset:08X};  // 写入测试值",
                        f"        trans.pstrb = 4'h{1 << (field.offset//8):X};",
                        f"        trans.secure = {1 if field.security == SecurityType.S.value else 0};",
                        f"        finish_item(trans);\n"
                    ])
                    
        seq_code.append("    endtask\nendclass")
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(seq_code))
            
    def generate_reg_model(self, output_path: str):
        """生成寄存器模型"""
        if not self.reg_model_gen.reg_models:
            self.reg_model_gen.load_excel()
            
        reg_code = ["""
package reg_model_pkg;
    import uvm_pkg::*;
    `include "uvm_macros.svh"
    
    // 寄存器基地址
    parameter REG_BASE_ADDR = 32'h0000_0000;
"""]

        # 生成每个寄存器的地址参数
        addr_offset = 0
        for reg_name in self.reg_model_gen.reg_models:
            reg_code.append(f"    parameter {reg_name}_ADDR = REG_BASE_ADDR + 'h{addr_offset:03X};")
            addr_offset += 4
            
        # 为每个寄存器生成寄存器类
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            reg_code.extend([
                f"\n    // {reg_name} 寄存器类",
                f"    class {reg_name}_reg extends uvm_reg;",
                f"        `uvm_object_utils({reg_name}_reg)\n"
            ])
            
            # 生成字段定义
            for field_name, field in reg_model.fields.items():
                reg_code.append(f"        rand uvm_reg_field {field_name};  // {field.description}")
                
            # 生成构造函数
            reg_code.extend([
                f"\n        function new(string name = \"{reg_name}_reg\");",
                f"            super.new(name, {reg_model.width}, UVM_NO_COVERAGE);",
                f"        endfunction\n"
            ])
            
            # 生成build函数
            reg_code.append("        virtual function void build();")
            
            # 配置每个字段
            for field_name, field in reg_model.fields.items():
                config = self.reg_model_gen.get_field_config(field)
                reg_code.extend([
                    f"            {field_name} = uvm_reg_field::type_id::create(\"{field_name}\");",
                    f"            {field_name}.configure(this, {field.width}, {field.offset}, ",
                    f"                \"{field.access_type}\", {1 if field.security == SecurityType.NS.value else 0}, ",
                    f"                {config['has_reset']}, {config['is_volatile']}, {config['is_rand']}, 0);"
                ])
                
            reg_code.append("        endfunction")
            reg_code.append("    endclass\n")
            
        # 生成寄存器块类
        reg_code.extend([
            "    // 寄存器块类",
            "    class reg_block extends uvm_reg_block;",
            "        `uvm_object_utils(reg_block)\n",
            "        // 寄存器实例"
        ])
        
        # 声明寄存器实例
        for reg_name in self.reg_model_gen.reg_models:
            reg_code.append(f"        rand {reg_name}_reg {reg_name.lower()};")
            
        # 生成构造函数和build函数
        reg_code.extend([
            "\n        function new(string name = \"reg_block\");",
            "            super.new(name, UVM_NO_COVERAGE);",
            "        endfunction\n",
            "        virtual function void build();",
            "            // 创建默认映射",
            "            default_map = create_map(\"default_map\", 0, 4, UVM_LITTLE_ENDIAN);\n"
        ])
        
        # 创建和配置每个寄存器
        addr_offset = 0
        for reg_name in self.reg_model_gen.reg_models:
            reg_code.extend([
                f"            // 创建{reg_name}寄存器",
                f"            {reg_name.lower()} = {reg_name}_reg::type_id::create(\"{reg_name.lower()}\");",
                f"            {reg_name.lower()}.configure(this);",
                f"            {reg_name.lower()}.build();",
                f"            default_map.add_reg({reg_name.lower()}, 'h{addr_offset:X});\n"
            ])
            addr_offset += 4
            
        reg_code.extend([
            "        endfunction",
            "    endclass",
            "endpackage"
        ])
        
        # 写入文件
        with open(output_path, 'w') as f:
            f.write('\n'.join(reg_code))

    def generate_adapter(self, output_path: str):
        """生成APB4适配器"""
        adapter_code = """
class apb4_adapter extends uvm_reg_adapter;
    `uvm_object_utils(apb4_adapter)
    
    function new(string name = "apb4_adapter");
        super.new(name);
        supports_byte_enable = 1;  // 支持字节写使能
        provides_responses = 1;    // 提供响应
    endfunction
    
    virtual function uvm_sequence_item reg2bus(const ref uvm_reg_bus_op rw);
        apb4_trans trans;
        trans = apb4_trans::type_id::create("trans");
        
        // 转换基本属性
        trans.paddr  = rw.addr;
        trans.pwrite = (rw.kind == UVM_WRITE);
        trans.pwdata = rw.data;
        trans.pstrb  = rw.byte_en;
        trans.secure = !rw.status[UVM_REG_IS_SECURE];  // 转换安全属性
        
        // 处理特殊访问类型
        case (rw.status[UVM_REG_ACCESS_TYPE])
            UVM_READ:  trans.pwrite = 0;
            UVM_WRITE: trans.pwrite = 1;
            UVM_READ_AFTER_WRITE: begin
                `uvm_error("APB4_ADAPTER", "APB4不支持读后写操作")
                return null;
            end
            default: begin
                `uvm_error("APB4_ADAPTER", $sformatf("不支持的访问类型: %s", rw.status[UVM_REG_ACCESS_TYPE]))
                return null;
            end
        endcase
        
        return trans;
    endfunction
    
    virtual function void bus2reg(uvm_sequence_item bus_item, ref uvm_reg_bus_op rw);
        apb4_trans trans;
        if (!$cast(trans, bus_item)) begin
            `uvm_fatal("APB4_ADAPTER", "总线项目类型转换失败")
            return;
        end
        
        // 转换基本属性
        rw.addr    = trans.paddr;
        rw.kind    = trans.pwrite ? UVM_WRITE : UVM_READ;
        rw.data    = trans.pwrite ? trans.pwdata : trans.prdata;
        rw.byte_en = trans.pstrb;
        rw.status  = trans.pslverr ? UVM_NOT_OK : UVM_IS_OK;
        
        // 设置安全属性
        rw.status[UVM_REG_IS_SECURE] = !trans.secure;
        
        // 设置访问类型
        rw.status[UVM_REG_ACCESS_TYPE] = trans.pwrite ? UVM_WRITE : UVM_READ;
    endfunction
    
    // 预测函数，用于处理特殊访问类型(如W1C, W1S等)
    virtual function void predict(uvm_reg_item rw);
        uvm_reg         rg;
        uvm_reg_field   field;
        uvm_reg_data_t  field_val;
        
        if (!$cast(rg, rw.element)) return;
        
        foreach (rg.get_fields(fields)) begin
            field = fields[index];
            case (field.get_access())
                "W1C": begin  // 写1清零
                    if (rw.kind == UVM_WRITE) begin
                        field_val = field.get();
                        if (rw.value[0][field.get_lsb_pos()]) 
                            field_val = 0;
                        field.predict(field_val);
                    end
                end
                "W1S": begin  // 写1置位
                    if (rw.kind == UVM_WRITE) begin
                        field_val = field.get();
                        if (rw.value[0][field.get_lsb_pos()])
                            field_val = 1;
                        field.predict(field_val);
                    end
                end
                "RC": begin  // 读清零
                    if (rw.kind == UVM_READ) begin
                        field.predict(0);
                    end
                end
                "RS": begin  // 读置位
                    if (rw.kind == UVM_READ) begin
                        field.predict(1);
                    end
                end
                "W0C": begin  // 写0清零
                    if (rw.kind == UVM_WRITE) begin
                        field_val = field.get();
                        if (!rw.value[0][field.get_lsb_pos()])
                            field_val = 0;
                        field.predict(field_val);
                    end
                end
                "W0S": begin  // 写0置位
                    if (rw.kind == UVM_WRITE) begin
                        field_val = field.get();
                        if (!rw.value[0][field.get_lsb_pos()])
                            field_val = 1;
                        field.predict(field_val);
                    end
                end
                "W1T": begin  // 写1触发
                    if (rw.kind == UVM_WRITE && rw.value[0][field.get_lsb_pos()]) begin
                        field.predict(1);
                        #1 field.predict(0);  // 一个周期后自动清零
                    end
                end
            endcase
        end
    endfunction
endclass
"""
        with open(output_path, 'w') as f:
            f.write(adapter_code)

    def generate_verif_env(self, output_dir: str):
        """生成完整的验证环境"""
        import os
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 生成寄存器模型
        self.generate_reg_model(f"{output_dir}/reg_model_pkg.sv")
            
        # 生成其他组件
        self.generate_interface(f"{output_dir}/apb4_if.sv")
        self.generate_adapter(f"{output_dir}/apb4_adapter.sv")
        self.generate_transaction(f"{output_dir}/apb4_trans.sv")
        self.generate_driver(f"{output_dir}/apb4_driver.sv")
        self.generate_monitor(f"{output_dir}/apb4_monitor.sv")
        self.generate_agent(f"{output_dir}/apb4_agent.sv")
        self.generate_sequences(f"{output_dir}/apb4_sequences.sv")
        
        # 生成包文件
        pkg_code = """
package apb4_verif_pkg;
    import uvm_pkg::*;
    import reg_model_pkg::*;
    `include "uvm_macros.svh"
    
    `include "apb4_adapter.sv"
    `include "apb4_trans.sv"
    `include "apb4_driver.sv"
    `include "apb4_monitor.sv"
    `include "apb4_agent.sv"
    `include "apb4_sequences.sv"
endpackage
"""
        with open(f"{output_dir}/apb4_verif_pkg.sv", 'w') as f:
            f.write(pkg_code) 