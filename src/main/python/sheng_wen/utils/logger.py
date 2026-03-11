import logging
import sys

# 1. 创建一个日志记录器实例。
#    可以自定义名称，例如使用应用程序包的根名称。
logger = logging.getLogger("sheng_wen")
logger.setLevel(logging.DEBUG) # 设置最低级别以捕获所有消息。

# 2. 防止日志消息传递给父级记录器，避免重复记录。
logger.propagate = False

# 3. 根据您的要求创建格式化器。
#    Kotlin 格式: "%-5level%d{YYYY-MM-dd HH:mm:ss.SSS}|%logger{18}%n %msg%n%n"
#    Python 翻译:
log_format = "%(levelname)-5.5s %(asctime)s.%(msecs)03d %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(log_format, date_format)

# 4. 创建一个处理器，将日志发送到控制台 (stdout)。
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(formatter)

# 5. 清除任何现有的处理器并添加新的，以避免重复。
#    这在代码可能被重新加载的环境中（如 Jupyter notebooks）非常重要。
if logger.hasHandlers():
    logger.handlers.clear()
logger.addHandler(handler)

# 现在，其他模块只需通过 `from src.main.python.sheng_wen.utils.logger import logger` 导入
# 并像这样使用: `logger.info("这是一条测试消息")`。
# logger 对象本身就是单例。

