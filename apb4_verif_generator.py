from typing import List, Dict
import pandas as pd
from reg_model_generator import RegModelGenerator, AccessType, SecurityType, RegModel, RegField
from pathlib import Path
import os

class APB4VerifGenerator:
    def __init__(self, excel_file: Path, uvm_home: Path):
        self.reg_model_gen = RegModelGenerator(excel_file)
        self.uvm_home = uvm_home
        
    def generate_interface(self, output_path: Path):
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
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(interface_code)
            
    def generate_transaction(self, output_path: Path):
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
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(trans_code)
            
    def generate_driver(self, output_path: Path):
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
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(driver_code)
            
    def generate_monitor(self, output_path: Path):
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
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(monitor_code)
            
    def generate_agent(self, output_path: Path):
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
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(agent_code)
            
    def generate_sequences(self, output_path: Path):
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
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(seq_code))
            
    def generate_reg_model(self, output_path: Path):
        """生成寄存器模型"""
        reg_code = ["""
    // 寄存器字段定义
    class reg_fields extends uvm_reg;"""]
        
        # 为每个字段生成UVM字段定义
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            for field_name, field in reg_model.fields.items():
                reg_code.extend([
                    f"    // {field_name} 字段",
                    f"    rand uvm_reg_field {reg_name.lower()}_{field_name};",
                    f"    // 配置字段属性",
                    f"    {reg_name.lower()}_{field_name}.configure(this, {field.width}, {field.offset}, ",
                    f"        \"{field.access_type}\", 0, {field.reset_value}, 1, 1, 1);"
                ])
        
        # 生成寄存器块类
        reg_code.extend([
            "endclass",
            "endpackage"
        ])
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(reg_code))

    def generate_adapter(self, output_path: Path):
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
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(adapter_code)

    def generate_env(self, output_path: Path):
        """生成 env.sv 文件"""
        env_code = """
`include "uvm_macros.svh"
import uvm_pkg::*;
import apb4_pkg::*;
import reg_model_pkg::*;

class apb4_env extends uvm_env;
    `uvm_component_utils(apb4_env)

    // 组件声明
    apb4_agent       agent;
    reg_model        reg_model;
    apb4_adapter     adapter;
    uvm_reg_predictor#(apb4_trans) predictor;
    apb4_scoreboard  scoreboard;
    apb4_coverage    coverage;

    function new(string name, uvm_component parent);
        super.new(name, parent);
    endfunction

    virtual function void build_phase(uvm_phase phase);
        super.build_phase(phase);

        // 创建组件
        agent = apb4_agent::type_id::create("agent", this);
        reg_model = reg_model::type_id::create("reg_model", this);
        adapter = apb4_adapter::type_id::create("adapter", this);
        predictor = uvm_reg_predictor#(apb4_trans)::type_id::create("predictor", this);
        scoreboard = apb4_scoreboard::type_id::create("scoreboard", this);
        coverage = apb4_coverage::type_id::create("coverage", this);

        // 配置寄存器模型
        reg_model.configure(null, "");
        reg_model.build();
        reg_model.lock_model();
    endfunction

    virtual function void connect_phase(uvm_phase phase);
        super.connect_phase(phase);

        // 连接寄存器模型和预测器
        predictor.map = reg_model.default_map;
        predictor.adapter = adapter;

        // 连接 agent 和预测器
        agent.monitor.ap.connect(predictor.bus_in);

        // 连接 agent 和 scoreboard
        agent.monitor.ap.connect(scoreboard.analysis_export);

        // 连接 agent 和 coverage
        agent.monitor.ap.connect(coverage.analysis_export);
    endfunction
endclass
"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(env_code)

    def generate_verif_env(self, config):
        """生成验证环境的逻辑"""
        print("生成验证环境...")
        
        # 生成 tb_top.sv 文件
        self.generate_tb_top(config.env_dir / "tb_top.sv")
        
        # 生成 tb.sv 文件
        self.generate_tb(config.env_dir / "tb.sv")
        
        # 生成 env.sv 文件
        self.generate_env(config.env_dir / "apb4_env.sv")
        
        print("验证环境生成完成")

    def generate_tb_top(self, output_path: Path):
        """生成 tb_top.sv 文件"""
        tb_top_code = """
module tb_top;
    // 信号定义
    reg clk;
    reg reset;

    // 实例化 DUT
    apb4_reg_block dut (
        .pclk(clk),
        .presetn(reset)
    );

    initial begin
        // 初始化信号
        clk = 0;
        reset = 1;
        #10 reset = 0;
        // 其他测试逻辑
    end

    always #5 clk = ~clk;  // 生成时钟信号
endmodule
"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tb_top_code)

    def generate_tb(self, output_path: Path):
        """生成 tb.sv 文件"""
        tb_code = """
module tb;
    // 信号定义
    reg clk;
    reg reset;

    // 实例化 DUT
    apb4_reg_block dut (
        .pclk(clk),
        .presetn(reset)
    );

    // 实例化 apb_env
    apb4_env env;

    initial begin
        // 初始化信号
        clk = 0;
        reset = 1;
        #10 reset = 0;

        // 创建并启动测试
        env = apb4_env::type_id::create("env", null);
        env.build();
        env.connect();
        env.start();
    end

    always #5 clk = ~clk;  // 生成时钟信号
endmodule
"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tb_code)

    def generate_tb_filelist(self, output_path: Path):
        """生成TB文件列表"""
        filelist = [
            "// UVM库路径",
            f"+incdir+{self.uvm_home}/src",  # 使用 UVM_HOME 环境变量
            f"{self.uvm_home}/src/uvm.sv"  # 使用 UVM_HOME 环境变量
        ]
        
        # 检查 UVM 库路径
        if (self.uvm_home / "src/uvm.sv").exists():
            filelist.append(f"+incdir+{self.uvm_home}/src")  # 使用 UVM_HOME 环境变量
            filelist.append(f"{self.uvm_home}/src/uvm.sv")   # 使用 UVM_HOME 环境变量
        else:
            print(f"警告: 找不到 UVM 库文件: {self.uvm_home}/src/uvm.sv")
            print("将使用 NO_DPI 模式编译")
            filelist.append("+define+UVM_NO_DPI")  # 添加 NO_DPI 定义

        filelist.extend([
            "",
            "// 寄存器模型",
            "${TEST}/tb/uvc/reg_model/reg_model_pkg.sv",
            "",
            "// APB4 UVC",
            "${TEST}/tb/uvc/apb4/apb4_pkg.sv",
            "${TEST}/tb/uvc/apb4/apb4_if.sv",
            "${TEST}/tb/uvc/apb4/apb4_types.sv",
            "${TEST}/tb/uvc/apb4/apb4_config.sv",
            "${TEST}/tb/uvc/apb4/apb4_driver.sv",
            "${TEST}/tb/uvc/apb4/apb4_monitor.sv",
            "${TEST}/tb/uvc/apb4/apb4_sequencer.sv",
            "${TEST}/tb/uvc/apb4/apb4_agent.sv",
            "",
            "// 验证环境",
            "${TEST}/tb/env/apb4_env.sv",
            "${TEST}/tb/env/test_top.sv",
            "${TEST}/tb/env/tb.sv",
            "",
            "// 测试用例",
            "${TEST}/tb/benchmark/sequence/apb4_base_sequence.sv",
            "${TEST}/tb/benchmark/sequence/apb4_reg_sequences.sv",
            "${TEST}/tb/benchmark/testcase/apb4_base_test.sv",
            "${TEST}/tb/benchmark/testcase/apb4_reg_tests.sv",
            "${TEST}/tb/benchmark/tc_include_lib/apb4_test_pkg.sv"
        ])
        
        # 确保父目录存在
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(filelist))

    def generate_apb4_components(self, output_dir: Path):
        """生成APB4相关组件"""
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

        # 生成APB4相关文件
        files = [
            "apb4_if.sv",
            "apb4_trans.sv",
            "apb4_driver.sv",
            "apb4_monitor.sv",
            "apb4_agent.sv"
        ]

        for file in files:
            file_path = output_dir / file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"// {file} 文件内容\n")
                # 这里可以添加具体的文件内容生成逻辑 