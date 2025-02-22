from typing import List, Dict
import pandas as pd
from reg_model_generator import RegModelGenerator, AccessType, SecurityType, RegModel, RegField

class RTLGenerator:
    def __init__(self, excel_file: str):
        self.reg_model_gen = RegModelGenerator(excel_file)
        self.module_name = "apb4_reg_block"
        
    def generate_field_logic(self, reg_name: str, field: RegField) -> List[str]:
        """生成字段逻辑"""
        logic = []
        field_mask = (1 << field.width) - 1
        field_range = f"[{field.offset + field.width - 1}:{field.offset}]"
        
        # 生成读逻辑
        if field.is_readable():
            if field.access_type == AccessType.RC.value:  # 读清零
                logic.extend([
                    f"    // {field.name} 读清零逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= {field.reset_value};",
                    f"        end else if (reg_read && paddr == {reg_name}_ADDR) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= 'h0;",
                    f"        end else if (hw_set_{reg_name.lower()}_{field.name}) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= hw_data_{reg_name.lower()}_{field.name};",
                    f"        end",
                    f"    end\n"
                ])
            elif field.access_type == AccessType.RS.value:  # 读置位
                logic.extend([
                    f"    // {field.name} 读置位逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= {field.reset_value};",
                    f"        end else if (reg_read && paddr == {reg_name}_ADDR) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= {field_mask};",
                    f"        end else if (hw_set_{reg_name.lower()}_{field.name}) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= hw_data_{reg_name.lower()}_{field.name};",
                    f"        end",
                    f"    end\n"
                ])
                
        # 生成写逻辑
        if field.is_writable():
            if field.access_type == AccessType.W1C.value:  # 写1清零
                logic.extend([
                    f"    // {field.name} 写1清零逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= {field.reset_value};",
                    f"        end else if (reg_write && paddr == {reg_name}_ADDR) begin",
                    f"            if (pwdata{field_range} & pstrb[{field.offset//8}]) begin",
                    f"                {reg_name.lower()}_reg{field_range} <= ",
                    f"                    {reg_name.lower()}_reg{field_range} & ~(pwdata{field_range} & {field_mask});",
                    f"            end",
                    f"        end else if (hw_set_{reg_name.lower()}_{field.name}) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= hw_data_{reg_name.lower()}_{field.name};",
                    f"        end",
                    f"    end\n"
                ])
            elif field.access_type == AccessType.W1S.value:  # 写1置位
                logic.extend([
                    f"    // {field.name} 写1置位逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= {field.reset_value};",
                    f"        end else if (reg_write && paddr == {reg_name}_ADDR) begin",
                    f"            if (pwdata{field_range} & pstrb[{field.offset//8}]) begin",
                    f"                {reg_name.lower()}_reg{field_range} <= ",
                    f"                    {reg_name.lower()}_reg{field_range} | (pwdata{field_range} & {field_mask});",
                    f"            end",
                    f"        end else if (hw_set_{reg_name.lower()}_{field.name}) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= hw_data_{reg_name.lower()}_{field.name};",
                    f"        end",
                    f"    end\n"
                ])
            elif field.access_type == AccessType.W0C.value:  # 写0清零
                logic.extend([
                    f"    // {field.name} 写0清零逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= {field.reset_value};",
                    f"        end else if (reg_write && paddr == {reg_name}_ADDR) begin",
                    f"            if (~pwdata{field_range} & pstrb[{field.offset//8}]) begin",
                    f"                {reg_name.lower()}_reg{field_range} <= ",
                    f"                    {reg_name.lower()}_reg{field_range} & (pwdata{field_range} | ~{field_mask});",
                    f"            end",
                    f"        end else if (hw_set_{reg_name.lower()}_{field.name}) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= hw_data_{reg_name.lower()}_{field.name};",
                    f"        end",
                    f"    end\n"
                ])
            elif field.access_type == AccessType.W0S.value:  # 写0置位
                logic.extend([
                    f"    // {field.name} 写0置位逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= {field.reset_value};",
                    f"        end else if (reg_write && paddr == {reg_name}_ADDR) begin",
                    f"            if (~pwdata{field_range} & pstrb[{field.offset//8}]) begin",
                    f"                {reg_name.lower()}_reg{field_range} <= ",
                    f"                    {reg_name.lower()}_reg{field_range} | (~pwdata{field_range} & {field_mask});",
                    f"            end",
                    f"        end else if (hw_set_{reg_name.lower()}_{field.name}) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= hw_data_{reg_name.lower()}_{field.name};",
                    f"        end",
                    f"    end\n"
                ])
            elif field.access_type == AccessType.W1T.value:  # 写1触发
                logic.extend([
                    f"    // {field.name} 写1触发逻辑",
                    f"    reg {reg_name.lower()}_{field.name}_trigger;",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_{field.name}_trigger <= 1'b0;",
                    f"        end else begin",
                    f"            {reg_name.lower()}_{field.name}_trigger <= ",
                    f"                reg_write && paddr == {reg_name}_ADDR && ",
                    f"                pwdata{field_range} & pstrb[{field.offset//8}];",
                    f"        end",
                    f"    end\n"
                ])
            else:  # RW, WO
                logic.extend([
                    f"    // {field.name} 标准读写逻辑",
                    f"    always @(posedge pclk) begin",
                    f"        if (!presetn) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= {field.reset_value};",
                    f"        end else if (reg_write && paddr == {reg_name}_ADDR && pstrb[{field.offset//8}]) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= pwdata{field_range} & {field_mask};",
                    f"        end else if (hw_set_{reg_name.lower()}_{field.name}) begin",
                    f"            {reg_name.lower()}_reg{field_range} <= hw_data_{reg_name.lower()}_{field.name};",
                    f"        end",
                    f"    end\n"
                ])
                
        return logic
        
    def generate_port_list(self) -> str:
        """生成模块端口列表"""
        ports = """
    // APB4接口信号
    input  wire                  pclk,
    input  wire                  presetn,
    input  wire                  psel,
    input  wire                  penable,
    input  wire [31:0]          paddr,
    input  wire                 pwrite,
    input  wire [31:0]          pwdata,
    input  wire [3:0]           pstrb,
    output reg                   pready,
    output reg                   pslverr,
    output reg  [31:0]          prdata,
    
    // 寄存器输出信号
"""
        # 添加每个寄存器的输出端口
        reg_groups = self.reg_model_gen.reg_models.groupby('RegisterName')
        for reg_name, fields in reg_groups:
            total_width = sum(fields['Width'])
            ports += f"    output reg  [{total_width-1}:0]     {reg_name.lower()}_o,\n"
            
        return ports.rstrip(',\n')
    
    def generate_reg_declarations(self) -> str:
        """生成寄存器声明"""
        reg_groups = self.reg_model_gen.reg_models.groupby('RegisterName')
        declarations = []
        
        # 生成地址参数定义
        declarations.append("    // 寄存器地址定义")
        addr_offset = 0
        for reg_name in reg_groups.groups.keys():
            declarations.append(f"    localparam {reg_name}_ADDR = 32'h{addr_offset:08X};")
            addr_offset += 4
            
        # 生成寄存器定义
        declarations.append("\n    // 寄存器定义")
        for reg_name, fields in reg_groups:
            total_width = sum(fields['Width'])
            declarations.append(f"    reg [{total_width-1}:0] {reg_name.lower()}_reg;")
            
        return '\n'.join(declarations)
    
    def generate_write_logic(self) -> str:
        """生成写逻辑"""
        reg_groups = self.reg_model_gen.reg_models.groupby('RegisterName')
        write_logic = []
        
        write_logic.append("""
    // 写逻辑
    always @(posedge pclk or negedge presetn) begin
        if (!presetn) begin""")
        
        # 复位值设置
        for reg_name, fields in reg_groups:
            reset_value = 0
            offset = 0
            for _, field in fields.iterrows():
                reset_value |= (field['Reset_value'] << offset)
                offset += field['Width']
            write_logic.append(f"            {reg_name.lower()}_reg <= {len(bin(reset_value)[2:])}\'h{reset_value:X};")
            
        write_logic.append("""        end
        else if (psel && penable && pwrite) begin
            case (paddr)""")
        
        # 写入逻辑
        addr_offset = 0
        for reg_name, fields in reg_groups:
            write_logic.append(f"                {reg_name}_ADDR: begin")
            
            # 生成每个字段的写入逻辑
            offset = 0
            for _, field in fields.iterrows():
                if field['RW-op'] in ['RW', 'WO']:  # 只处理可写字段
                    mask = (1 << field['Width']) - 1
                    write_logic.append(
                        f"                    if (pstrb[{offset//8}]) "
                        f"{reg_name.lower()}_reg[{offset+field['Width']-1}:{offset}] <= "
                        f"pwdata[{offset+field['Width']-1}:{offset}];"
                    )
                offset += field['Width']
                
            write_logic.append("                end")
            addr_offset += 4
            
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
        reg_groups = self.reg_model_gen.reg_models.groupby('RegisterName')
        read_logic = []
        
        read_logic.append("""
    // 读逻辑
    always @(posedge pclk or negedge presetn) begin
        if (!presetn) begin
            prdata <= 32'h0;
            pslverr <= 1'b0;
        end
        else if (psel && !pwrite) begin
            case (paddr)""")
            
        # 读取逻辑
        addr_offset = 0
        for reg_name, fields in reg_groups:
            read_logic.append(f"                {reg_name}_ADDR: begin")
            read_logic.append(f"                    prdata <= {{32-$bits({reg_name.lower()}_reg){{1'b0}}, {reg_name.lower()}_reg}};")
            read_logic.append("                end")
            addr_offset += 4
            
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
        reg_groups = self.reg_model_gen.reg_models.groupby('RegisterName')
        assignments = ["\n    // 输出赋值"]
        
        for reg_name in reg_groups.groups.keys():
            assignments.append(f"    assign {reg_name.lower()}_o = {reg_name.lower()}_reg;")
            
        return '\n'.join(assignments)
    
    def generate_rtl(self, output_path: str):
        """生成完整的RTL代码"""
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
        
        # 写入文件
        with open(output_path, 'w') as f:
            f.write('\n'.join(rtl_code)) 