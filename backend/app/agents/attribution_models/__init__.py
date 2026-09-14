"""归因计算插件模型体系"""

# 导入各模型文件以触发 @registry.register() 装饰器
from app.agents.attribution_models import (
    first_touch,
    last_touch,
    linear,
    time_decay,
    position_decay,
    data_driven,
    custom,
)