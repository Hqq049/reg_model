from typing import List, Dict
import pandas as pd
from pathlib import Path

class CoverageGenerator:
    def __init__(self, reg_model):
        self.reg_model = reg_model
        
    def generate_field_coverage(self, field_name: str, width: int, access: str) -> str:
        """生成单个字段的覆盖点定义"""
        if access != 'RW':  # 只对可读写字段生成覆盖率
            return ""
            
        return f"""
            // {field_name} 字段覆盖点
            {field_name}_cp: coverpoint {field_name}.value {{
                bins valid_values[] = {{[0:{'{'}{(1 << width)-1}{'}'}}};
                bins transitions[] = ([0:{'{'}{(1 << width)-1}{'}'} => 0:{'{'}{(1 << width)-1}{'}'}]);
                option.at_least = 1;
            }}"""
    
    def generate_reg_coverage(self, reg_name: str, fields: pd.DataFrame) -> str:
        """生成单个寄存器的覆盖率代码"""
        coverage_code = [f"""
        // {reg_name} 寄存器覆盖率类
        class {reg_name}_cov extends uvm_subscriber #(uvm_reg_item);
            `uvm_component_utils({reg_name}_cov)
            
            // 覆盖率组定义
            covergroup reg_cg;"""]
        
        # 生成每个字段的覆盖点
        field_coverpoints = []
        rw_fields = []
        for _, field in fields.iterrows():
            if field['RW-op'] == 'RW':
                field_coverpoints.append(
                    self.generate_field_coverage(field['Filed'], field['Width'], field['RW-op'])
                )
                rw_fields.append(field['Filed'])
        
        coverage_code.extend(field_coverpoints)
        
        # 添加字段交叉覆盖
        if len(rw_fields) > 1:
            cross_fields = ' , '.join([f"{field}_cp" for field in rw_fields])
            coverage_code.append(f"""
                // 字段交叉覆盖
                field_cross: cross {cross_fields};""")
        
        # 添加覆盖率组实现
        coverage_code.extend(["""
            endgroup
            
            // 寄存器模型引用
            {reg_name}_reg reg_model;
            
            function new(string name, uvm_component parent);
                super.new(name, parent);
                reg_cg = new();
            endfunction
            
            function void build_phase(uvm_phase phase);
                super.build_phase(phase);
                reg_model = {reg_name}_reg::type_id::create("reg_model");
            endfunction
            
            // 采样函数
            virtual function void write(uvm_reg_item t);
                if(t.element_kind == UVM_REG) begin
                    reg_cg.sample();
                end
            endfunction
        endclass
        """])
        
        return '\n'.join(coverage_code)
    
    def generate_coverage_pkg(self, output_path: str):
        """生成覆盖率包文件"""
        if self.reg_model.reg_data is None:
            self.reg_model.load_excel()
            
        # 按寄存器名称分组
        reg_groups = self.reg_model.reg_data.groupby('RegisterName')
        
        # 生成覆盖率包
        output_code = ["""
        package reg_coverage_pkg;
            import uvm_pkg::*;
            import reg_model_pkg::*;
            `include "uvm_macros.svh"
            
            // 覆盖率收集基类
            virtual class reg_coverage_base extends uvm_subscriber #(uvm_reg_item);
                function new(string name, uvm_component parent);
                    super.new(name, parent);
                endfunction
                
                pure virtual function void write(uvm_reg_item t);
            endclass
        """]
        
        # 为每个寄存器生成覆盖率类
        for reg_name, fields in reg_groups:
            output_code.append(self.generate_reg_coverage(reg_name, fields))
        
        # 生成顶层覆盖率类
        output_code.append("""
            // 顶层覆盖率类
            class reg_coverage extends uvm_component;
                `uvm_component_utils(reg_coverage)
                
                // 覆盖率实例
        """)
        
        # 添加覆盖率实例
        for reg_name in reg_groups.groups.keys():
            output_code.append(f"    {reg_name}_cov {reg_name}_coverage;")
        
        # 添加构造函数和build_phase
        output_code.extend(["""
                function new(string name, uvm_component parent);
                    super.new(name, parent);
                endfunction
                
                function void build_phase(uvm_phase phase);
                    super.build_phase(phase);
        """])
        
        # 创建覆盖率实例
        for reg_name in reg_groups.groups.keys():
            output_code.append(
                f"            {reg_name}_coverage = {reg_name}_cov::type_id::create(\"{reg_name}_coverage\", this);"
            )
        
        # 结束类定义
        output_code.extend(["""
                endfunction
            endclass
            
        endpackage
        """])
        
        # 写入文件
        with open(output_path, 'w') as f:
            f.write('\n'.join(output_code))

    def generate_coverage(self, output_path: Path):
        """生成覆盖率收集代码"""
        cov_code = ["""
        // 字段覆盖率组
        covergroup field_cg;"""]
        
        # 为每个字段生成覆盖点
        for reg_name, reg_model in self.reg_model_gen.reg_models.items():
            for field_name, field in reg_model.fields.items():
                cov_code.extend([
                    f"        // {field_name} 覆盖点",
                    f"        {reg_name.lower()}_{field_name}_cp: coverpoint " +
                    f"reg_model.{reg_name.lower()}_{field_name}.value {{",
                    f"            bins valid_values[] = {{[0:{(1 << field.width)-1}]}};",
                    f"        }}"
                ]) 