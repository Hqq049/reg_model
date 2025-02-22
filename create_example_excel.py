import pandas as pd
import numpy as np

# 创建示例寄存器数据
data = {
    'RegisterName': [
        'CTRL',     'CTRL',     'CTRL',      # 控制寄存器
        'STATUS',   'STATUS',   'STATUS',    # 状态寄存器
        'DATA',     'DATA',                  # 数据寄存器
        'VERSION',  'VERSION'                # 版本寄存器
    ],
    'Filed': [
        'enable',   'mode',     'int_en',    # CTRL字段
        'busy',     'error',    'ready',     # STATUS字段
        'data_h',   'data_l',               # DATA字段
        'major',    'minor'                 # VERSION字段
    ],
    'Width': [
        1,          2,          1,           # CTRL位宽
        1,          2,          1,           # STATUS位宽
        16,         16,                     # DATA位宽
        4,          4                       # VERSION位宽
    ],
    'RW-op': [
        'RW',       'RW',       'RW',        # CTRL访问权限
        'RO',       'RO',       'RO',        # STATUS访问权限
        'RW',       'RW',                   # DATA访问权限
        'RO',       'RO'                    # VERSION访问权限
    ],
    'Reset_value': [
        0,          0,          0,           # CTRL复位值
        0,          0,          1,           # STATUS复位值
        0,          0,                      # DATA复位值
        1,          0                       # VERSION复位值
    ],
    'NON-SECURE': [
        0,          0,          0,           # CTRL安全属性
        0,          0,          0,           # STATUS安全属性
        1,          1,                      # DATA安全属性
        0,          0                       # VERSION安全属性
    ],
    'Description': [
        '模块使能控制',  '工作模式选择',  '中断使能控制',    # CTRL描述
        '忙状态指示',    '错误状态',      '就绪状态',       # STATUS描述
        '数据高16位',    '数据低16位',                    # DATA描述
        '主版本号',      '次版本号'                      # VERSION描述
    ]
}

# 创建DataFrame
df = pd.DataFrame(data)

# 保存到Excel文件
excel_file = "register_spec.xlsx"
df.to_excel(excel_file, index=False)

print(f"已生成示例寄存器定义Excel文件: {excel_file}")

# 显示预览
print("\n寄存器定义预览:")
print(df.to_string()) 