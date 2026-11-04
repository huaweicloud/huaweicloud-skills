"""bag2manifest: 从 ROS2 bag 生成 LeRobotDataset v3.0 配置 (manifest.yaml) 的本地工具.

模块划分:
    reader   : bag 读取抽象层 (mcap / db3, 无需安装 ROS, 不依赖 metadata.yaml)
    msgutil  : 消息类型分类 / 数值字段展平 / 图像解码
    profiler : 扫描 bag 产出 profile.json
    infer    : 映射推断规则 —— 唯一真相源, Web 端不得重写
    derive   : 计算字段表达式 (AST 白名单安全求值)
    manifest : profile + 用户选择 -> manifest.yaml
    webapp   : Gradio 可视化配置工作台
"""

__version__ = "0.2.0"
PROFILE_SCHEMA_VERSION = "1.0"
MANIFEST_SCHEMA_VERSION = "2.0"
