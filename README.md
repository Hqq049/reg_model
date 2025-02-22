# 寄存器模型自动生成工具

本工具用于自动生成APB4接口的寄存器RTL代码和UVM验证环境。

## 安装依赖

```bash
pip install pandas openpyxl python-docx
```

## 使用步骤

1. 运行脚本生成Excel模板：
```bash
python main.py
```

2. 填写register_spec.xlsx中的寄存器定义，格式如下：

| RegisterName | Filed | Width | RW-op | Reset_value | NON-SECURE | Description |
|-------------|-------|--------|-------|-------------|------------|-------------|
| CTRL        | enable| 1      | RW    | 0          | 0          | 使能控制位   |
| CTRL        | mode  | 2      | RW    | 0          | 0          | 工作模式     |
| STATUS      | busy  | 1      | RO    | 0          | 0          | 忙状态标志   |

说明：
- RegisterName: 寄存器名称
- Filed: 字段名称
- Width: 位宽
- RW-op: 读写属性(RW=读写，RO=只读)
- Reset_value: 复位值
- NON-SECURE: 安全属性(0=安全，1=非安全)
- Description: 描述信息

3. 再次运行脚本生成所有文件：
```bash
python main.py
```

## 输出文件说明

生成的文件将保存在output目录下：
- apb4_reg_block.v: APB4接口的寄存器RTL代码
- verif/: UVM验证环境
  - apb4_reg_pkg.sv: 验证环境包
  - tests/: 测试用例
    - apb4_reg_access_test.sv: 访问权限测试
    - apb4_reg_concurrent_test.sv: 并发访问测试
    - apb4_reg_error_test.sv: 错误注入测试
    - apb4_reg_burst_test.sv: 突发传输测试
- register_report.docx: 详细设计报告