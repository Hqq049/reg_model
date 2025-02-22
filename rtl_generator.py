from typing import List, Dict
import pandas as pd
from reg_model_generator import RegModelGenerator, AccessType, SecurityType, RegModel, RegField
from pathlib import Path

class RTLGenerator:
    def __init__(self, excel_file: Path):
        self.reg_model_gen = RegModelGenerator(excel_file)
        self.module_name = "apb4_reg_block"
        
    def generate_field_logic(self, reg_name: str, field: RegField) -> List[str]:
        """生成字段逻辑"""
        logic = []
        field_mask = (1 << field.width) - 1
        field_name = field.name
        
        # 生成读逻辑
        if field.is_readable():
            if field.access_type == AccessType.RC.value:  # 读清零
                logic.extend([
                    f"    // {field_name} 读清零逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_{field_name} <= {field.reset_value};",
                    f"        end else if (reg_read && paddr == {reg_name}_ADDR) begin",
                    f"            {reg_name.lower()}_{field_name} <= 'h0;",
                    f"        end else if (hw_set_{reg_name.lower()}_{field_name}) begin",
                    f"            {reg_name.lower()}_{field_name} <= hw_data_{reg_name.lower()}_{field_name};",
                    f"        end",
                    f"    end\n"
                ])
            elif field.access_type == AccessType.RS.value:  # 读置位
                logic.extend([
                    f"    // {field_name} 读置位逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_{field_name} <= {field.reset_value};",
                    f"        end else if (reg_read && paddr == {reg_name}_ADDR) begin",
                    f"            {reg_name.lower()}_{field_name} <= {field_mask};",
                    f"        end else if (hw_set_{reg_name.lower()}_{field_name}) begin",
                    f"            {reg_name.lower()}_{field_name} <= hw_data_{reg_name.lower()}_{field_name};",
                    f"        end",
                    f"    end\n"
                ])
                
        # 生成写逻辑
        if field.is_writable():
            if field.access_type == AccessType.W1C.value:  # 写1清零
                logic.extend([
                    f"    // {field_name} 写1清零逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_{field_name} <= {field.reset_value};",
                    f"        end else if (reg_write && paddr == {reg_name}_ADDR) begin",
                    f"            if (pwdata[{field.offset}] & pstrb[{field.offset//8}]) begin",
                    f"                {reg_name.lower()}_{field_name} <= ",
                    f"                    {reg_name.lower()}_{field_name} & ~pwdata[{field.offset}];",
                    f"            end",
                    f"        end else if (hw_set_{reg_name.lower()}_{field_name}) begin",
                    f"            {reg_name.lower()}_{field_name} <= hw_data_{reg_name.lower()}_{field_name};",
                    f"        end",
                    f"    end\n"
                ])
            elif field.access_type == AccessType.W1S.value:  # 写1置位
                logic.extend([
                    f"    // {field_name} 写1置位逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_{field_name} <= {field.reset_value};",
                    f"        end else if (reg_write && paddr == {reg_name}_ADDR) begin",
                    f"            if (pwdata[{field.offset//8}]) begin",
                    f"                {reg_name.lower()}_{field_name} <= ",
                    f"                    {reg_name.lower()}_{field_name} | (pwdata[{field.offset//8}] & {field_mask});",
                    f"            end",
                    f"        end else if (hw_set_{reg_name.lower()}_{field_name}) begin",
                    f"            {reg_name.lower()}_{field_name} <= hw_data_{reg_name.lower()}_{field_name};",
                    f"        end",
                    f"    end\n"
                ])
            elif field.access_type == AccessType.W0C.value:  # 写0清零
                logic.extend([
                    f"    // {field_name} 写0清零逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_{field_name} <= {field.reset_value};",
                    f"        end else if (reg_write && paddr == {reg_name}_ADDR) begin",
                    f"            if (~pwdata[{field.offset//8}]) begin",
                    f"                {reg_name.lower()}_{field_name} <= ",
                    f"                    {reg_name.lower()}_{field_name} & (pwdata[{field.offset//8}] | ~{field_mask});",
                    f"            end",
                    f"        end else if (hw_set_{reg_name.lower()}_{field_name}) begin",
                    f"            {reg_name.lower()}_{field_name} <= hw_data_{reg_name.lower()}_{field_name};",
                    f"        end",
                    f"    end\n"
                ])
            elif field.access_type == AccessType.W0S.value:  # 写0置位
                logic.extend([
                    f"    // {field_name} 写0置位逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_{field_name} <= {field.reset_value};",
                    f"        end else if (reg_write && paddr == {reg_name}_ADDR) begin",
                    f"            if (~pwdata[{field.offset//8}]) begin",
                    f"                {reg_name.lower()}_{field_name} <= ",
                    f"                    {reg_name.lower()}_{field_name} | (~pwdata[{field.offset//8}] & {field_mask});",
                    f"            end",
                    f"        end else if (hw_set_{reg_name.lower()}_{field_name}) begin",
                    f"            {reg_name.lower()}_{field_name} <= hw_data_{reg_name.lower()}_{field_name};",
                    f"        end",
                    f"    end\n"
                ])
            elif field.access_type == AccessType.W1T.value:  # 写1触发
                logic.extend([
                    f"    // {field_name} 写1触发逻辑",
                    f"    reg {reg_name.lower()}_{field_name}_trigger;",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_{field_name}_trigger <= 1'b0;",
                    f"        end else begin",
                    f"            {reg_name.lower()}_{field_name}_trigger <= ",
                    f"                reg_write && paddr == {reg_name}_ADDR && ",
                    f"                pwdata[{field.offset//8}];",
                    f"        end",
                    f"    end\n"
                ])
            else:  # RW, WO
                logic.extend([
                    f"    // {field_name} 标准读写逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_{field_name} <= {field.reset_value};",
                    f"        end else if (reg_write && paddr == {reg_name}_ADDR && pstrb[{field.offset//8}]) begin",
                    f"            {reg_name.lower()}_{field_name} <= pwdata[{field.offset + field.width - 1}:{field.offset}];",
                    f"        end else if (hw_set_{reg_name.lower()}_{field_name}) begin",
                    f"            {reg_name.lower()}_{field_name} <= hw_data_{reg_name.lower()}_{field_name};",
                    f"        end",
                    f"    end\n"
                ])
                
        return logic
        
    def generate_port_list(self) -> str:
        """生成模块端口列表"""
        if not self.reg_model_gen.reg_models:
            self.reg_model_gen.load_excel()
            
        ports = [
            "    // APB4接口信号",
            "    input  wire         pclk,",
            "    input  wire         presetn,",
            "    input  wire         psel,",
            "    input  wire         penable,",
            "    input  wire [31:0]  paddr,",
            "    input  wire         pwrite,",
            "    input  wire [31:0]  pwdata,",
            "    input  wire [3:0]   pstrb,",
            "    output reg          pready,",
            "    output reg          pslverr,",
            "    output reg  [31:0]  prdata"
        ]
        
        # 添加每个寄存器的输出端口
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            ports.append(f"    // {reg_name} 寄存器")
            ports.append(f"    output reg [{reg_model.width-1}:0] {reg_name.lower()}_o")
            
        return ",\n".join(ports)
    
    def generate_reg_declarations(self) -> str:
        """生成寄存器声明"""
        if not self.reg_model_gen.reg_models:
            self.reg_model_gen.load_excel()
            
        declarations = []
        
        # 生成地址参数定义
        declarations.append("    // 寄存器地址定义")
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            declarations.append(f"    localparam {reg_name}_ADDR = 32'h{reg_model.offset:08X};")
            
        # 生成字段定义
        declarations.append("\n    // 寄存器字段定义")
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            for field_name, field in reg_model.fields.items():
                declarations.append(
                    f"    reg [{field.width-1}:0] {reg_name.lower()}_{field_name};  // {field.description}"
                )
            
        return '\n'.join(declarations)
    
    def generate_write_logic(self) -> str:
        """生成写逻辑"""
        if not self.reg_model_gen.reg_models:
            self.reg_model_gen.load_excel()
            
        write_logic = []
        
        write_logic.append("""
    // 写逻辑
    always @(posedge pclk or negedge presetn) begin
        if (!presetn) begin""")
        
        # 复位值设置 - 使用字段名
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            for field_name, field in reg_model.fields.items():
                write_logic.append(
                    f"            {reg_name.lower()}_{field_name} <= {field.width}'h{field.reset_value:X};"
                )
                
        write_logic.append("""        end
        else if (psel && penable && pwrite) begin
            case (paddr)""")
        
        # 写入逻辑 - 使用字段名
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            write_logic.append(f"                {reg_name}_ADDR: begin")
            
            # 生成每个字段的写入逻辑
            for field_name, field in reg_model.fields.items():
                if field.is_writable():  # 只处理可写字段
                    write_logic.append(
                        f"                    if (pstrb[{field.offset//8}]) "
                        f"{reg_name.lower()}_{field_name} <= "
                        f"pwdata[{field.offset + field.width - 1}:{field.offset}];"
                    )
                
            write_logic.append("                end")
            
        write_logic.extend([
            "                default: begin",
            "                    pslverr <= 1'b1;",
            "                end",
            "            endcase",
            "        end",
            "    end"
        ])
        
        return '\n'.join(write_logic)
    
    def generate_read_logic(self) -> str:
        """生成读逻辑"""
        if not self.reg_model_gen.reg_models:
            self.reg_model_gen.load_excel()
            
        read_logic = ["""
    // 读逻辑
    always @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            prdata <= 32'h0;
            pslverr <= 1'b0;
        end
        else if (psel && !pwrite) begin
            case (paddr)"""]
        
        # 读取逻辑 - 使用字段拼接
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            read_logic.append(f"                {reg_name}_ADDR: begin")
            read_logic.append("                    prdata <= {")
            
            # 按字段顺序拼接
            fields_sorted = sorted(reg_model.fields.items(), 
                                 key=lambda x: x[1].offset, reverse=True)
            field_reads = []
            for field_name, field in fields_sorted:
                field_reads.append(f"{reg_name.lower()}_{field_name}")
            
            read_logic.append(f"                        {', '.join(field_reads)}")
            read_logic.append("                    };")
            read_logic.append("                end")
        
        read_logic.extend([
            "                default: begin",
            "                    prdata <= 32'h0;",
            "                    pslverr <= 1'b1;",
            "                end",
            "            endcase",
            "        end",
            "    end"
        ])
        
        return '\n'.join(read_logic)
    
    def generate_output_assignments(self) -> str:
        """生成输出赋值"""
        assignments = ["\n    // 输出赋值"]
        
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            # 按字段拼接输出
            fields_sorted = sorted(reg_model.fields.items(), 
                                 key=lambda x: x[1].offset, reverse=True)
            field_names = [f"{reg_name.lower()}_{f[0]}" for f in fields_sorted]
            assignments.append(
                f"    assign {reg_name.lower()}_o = {{{', '.join(field_names)}}};"
            )
        
        return '\n'.join(assignments)
    
    def generate_rtl(self, output_path: Path):
        """生成RTL代码"""
        if not self.reg_model_gen.reg_models:
            self.reg_model_gen.load_excel()
        
        rtl_code = [
            "// APB4寄存器模块",
            f"module {self.module_name} (",
            self.generate_port_list(),
            ");\n",
            self.generate_reg_declarations(),
            self.generate_write_logic(),
            self.generate_read_logic(),
            self.generate_output_assignments(),
            "\nendmodule"
        ]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(rtl_code))

    def generate_filelist(self, output_path: Path):
        """生成文件列表"""
        filelist = [
            "// RTL文件列表",
            "+incdir+${TEST}/dut/rtl",
            "",
            "// APB4寄存器模块",
            "${TEST}/dut/rtl/apb4_reg_block.v"
        ]
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(filelist)) 