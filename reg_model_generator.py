import pandas as pd
from typing import List, Dict, Optional
from create_excel import ExcelGenerator
from enum import Enum, auto

class AccessType(Enum):
    """寄存器访问类型"""
    RW = "RW"    # 读写
    RO = "RO"    # 只读
    WO = "WO"    # 只写
    W1C = "W1C"  # 写1清零
    W1S = "W1S"  # 写1置位
    RC = "RC"    # 读清零
    RS = "RS"    # 读置位
    WC = "WC"    # 写清零
    WS = "WS"    # 写置位
    W1T = "W1T"  # 写1触发
    W0C = "W0C"  # 写0清零
    W0S = "W0S"  # 写0置位

class SecurityType(Enum):
    """安全属性类型"""
    S = "S"      # 安全
    NS = "NS"    # 非安全

class RegField:
    """寄存器字段类"""
    def __init__(self, name: str, width: int, offset: int, access_type: str, 
                 security: str, reset_value: int, description: str):
        self.name = name
        self.width = width
        self.offset = offset
        self.access_type = access_type
        self.security = security
        self.reset_value = reset_value
        self.description = description
        
    def is_readable(self) -> bool:
        """检查字段是否可读"""
        return self.access_type in [at.value for at in [
            AccessType.RW, AccessType.RO, AccessType.RC, AccessType.RS
        ]]
        
    def is_writable(self) -> bool:
        """检查字段是否可写"""
        return self.access_type in [at.value for at in [
            AccessType.RW, AccessType.WO, AccessType.W1C, AccessType.W1S,
            AccessType.WC, AccessType.WS, AccessType.W1T,
            AccessType.W0C, AccessType.W0S
        ]]
        
    def get_hw_access(self) -> str:
        """获取硬件访问类型"""
        if self.access_type in [AccessType.RC.value, AccessType.RS.value]:
            return "RW"  # 硬件可读写
        elif self.access_type in [AccessType.RO.value]:
            return "WO"  # 硬件只写
        elif self.access_type in [AccessType.WO.value]:
            return "RO"  # 硬件只读
        else:
            return "RW"  # 默认硬件可读写

class RegModel:
    """寄存器模型类"""
    def __init__(self, name: str, fields: pd.DataFrame):
        self.name = name
        self.fields: Dict[str, RegField] = {}
        self.width = 0
        self.offset = 0
        
        # 创建字段
        current_offset = 0
        for _, row in fields.iterrows():
            field = RegField(
                name=row['Filed'],
                width=row['Width'],
                offset=current_offset,
                access_type=row['RW-op'],
                security=row['Security'],
                reset_value=row['Reset_value'],
                description=row['Description']
            )
            self.fields[row['Filed']] = field
            current_offset += row['Width']
        self.width = current_offset
        
    def get_reset_value(self) -> int:
        """计算寄存器的复位值"""
        reset_value = 0
        for field in self.fields.values():
            reset_value |= (field.reset_value << field.offset)
        return reset_value
    
    def is_secure(self) -> bool:
        """检查寄存器是否为安全寄存器"""
        return all(field.security == SecurityType.S.value 
                  for field in self.fields.values())
    
    def get_access_str(self) -> str:
        """获取寄存器的访问字符串描述"""
        accesses = set(field.access_type for field in self.fields.values())
        return ", ".join(sorted(accesses))

class RegModelGenerator:
    """寄存器模型生成器"""
    def __init__(self, excel_file: str):
        self.excel_file = excel_file
        self.reg_data = None
        self.reg_models: Dict[str, RegModel] = {}
        self.base_address = 0x0
        self.address_width = 32
        self.data_width = 32
        
    def load_excel(self):
        """加载Excel文件并创建寄存器模型"""
        excel_gen = ExcelGenerator()
        self.reg_data = excel_gen.read_excel(self.excel_file)
        
        # 按寄存器名称分组
        reg_groups = self.reg_data.groupby('RegisterName')
        
        # 创建寄存器模型
        offset = 0
        for reg_name, fields in reg_groups:
            reg_model = RegModel(reg_name, fields)
            reg_model.offset = offset
            self.reg_models[reg_name] = reg_model
            offset += 4  # 每个寄存器4字节对齐
            
    def get_field_config(self, field: RegField) -> Dict[str, int]:
        """获取字段配置参数"""
        configs = {
            AccessType.RW.value: {'is_rand': 1, 'has_reset': 1, 'is_volatile': 0},
            AccessType.RO.value: {'is_rand': 0, 'has_reset': 1, 'is_volatile': 1},
            AccessType.WO.value: {'is_rand': 1, 'has_reset': 0, 'is_volatile': 0},
            AccessType.W1C.value: {'is_rand': 1, 'has_reset': 1, 'is_volatile': 1},
            AccessType.W1S.value: {'is_rand': 1, 'has_reset': 1, 'is_volatile': 1},
            AccessType.RC.value: {'is_rand': 0, 'has_reset': 1, 'is_volatile': 1},
            AccessType.RS.value: {'is_rand': 0, 'has_reset': 1, 'is_volatile': 1},
            AccessType.WC.value: {'is_rand': 1, 'has_reset': 1, 'is_volatile': 1},
            AccessType.WS.value: {'is_rand': 1, 'has_reset': 1, 'is_volatile': 1},
            AccessType.W1T.value: {'is_rand': 1, 'has_reset': 0, 'is_volatile': 1},
            AccessType.W0C.value: {'is_rand': 1, 'has_reset': 1, 'is_volatile': 1},
            AccessType.W0S.value: {'is_rand': 1, 'has_reset': 1, 'is_volatile': 1}
        }
        return configs.get(field.access_type, configs[AccessType.RW.value])
    
    def generate_reg_model(self, output_path: str):
        """生成寄存器模型代码"""
        if self.reg_data is None:
            self.load_excel()
            
        # 按寄存器名称分组
        reg_groups = self.reg_data.groupby('RegisterName')
        
        # 生成寄存器包
        output_code = ["""
        package reg_model_pkg;
            import uvm_pkg::*;
            `include "uvm_macros.svh"
            
            // 寄存器基地址
            parameter REG_BASE_ADDR = 32'h0000_0000;
        """]
        
        # 生成每个寄存器的地址参数
        addr_offset = 0
        for reg_name in reg_groups.groups.keys():
            output_code.append(f"    parameter {reg_name}_ADDR = REG_BASE_ADDR + 'h{addr_offset:03X};")
            addr_offset += 4
        
        # 生成每个寄存器类
        for reg_name, fields in reg_groups:
            # 计算字段偏移
            field_offsets = self.calculate_field_offset(fields)
            
            # 生成字段定义
            field_definitions = []
            field_builds = []
            
            for _, field in fields.iterrows():
                # 生成rand变量定义
                field_definitions.append(f"rand uvm_reg_field {field['Filed']};")
                
                # 生成build函数中的字段配置
                config = self.get_field_config(field)
                field_builds.append(f"""
                    {field['Filed']} = uvm_reg_field::type_id::create("{field['Filed']}");
                    {field['Filed']}.configure(this, {field['Width']}, {field_offsets[field['Filed']]}, 
                        "{field['RW-op']}", {self.convert_security_to_nonsecure(field['Security'])}, 
                        {config['has_reset']}, {config['is_volatile']}, {config['is_rand']}, 0);
                """)
            
            # 使用模板生成寄存器类
            reg_code = f"""
            class {reg_name}_reg extends uvm_reg;
                `uvm_object_utils({reg_name}_reg)
                
                // 字段定义
                {'\n    '.join(field_definitions)}
                
                function new(string name = "{reg_name}_reg");
                    super.new(name, {self.data_width}, UVM_NO_COVERAGE);
                endfunction
                
                virtual function void build();
                    {'\n        '.join(field_builds)}
                endfunction
                
                // 添加寄存器描述
                `uvm_register_description("{'; '.join(fields['Description'])}")
            endclass
            """
            output_code.append(reg_code)
        
        # 生成寄存器块类
        output_code.append("""
            class reg_block extends uvm_reg_block;
                `uvm_object_utils(reg_block)
                
                // 寄存器实例定义
        """)
        
        # 添加寄存器实例
        for reg_name in reg_groups.groups.keys():
            output_code.append(f"    {reg_name}_reg {reg_name.lower()};")
        
        # 添加build函数
        build_code = ["""
                function new(string name = "reg_block");
                    super.new(name, UVM_NO_COVERAGE);
                endfunction
                
                virtual function void build();
        """]
        
        # 创建和配置每个寄存器
        addr_offset = 0
        for reg_name in reg_groups.groups.keys():
            build_code.extend([
                f"            {reg_name.lower()} = {reg_name}_reg::type_id::create(\"{reg_name.lower()}\");",
                f"            {reg_name.lower()}.configure(this);",
                f"            {reg_name.lower()}.build();",
                f"            default_map.add_reg({reg_name.lower()}, 'h{addr_offset:03X});"
            ])
            addr_offset += 4
        
        build_code.append("        endfunction")
        output_code.extend(build_code)
        output_code.append("    endclass")
        output_code.append("endpackage")
        
        # 写入文件
        with open(output_path, 'w') as f:
            f.write('\n'.join(output_code))
        
    def generate_rtl(self, output_path: str):
        """生成RTL代码"""
        if self.reg_data is None:
            self.load_excel()
            
        # TODO: 实现RTL生成逻辑
        pass 