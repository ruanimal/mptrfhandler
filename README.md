# MultProcTimedRotatingFileHandler
支持按时间滚动的Python多进程日志Handler, 支支持macOS/Linux, 自用未充分测试

参考了 https://github.com/yorks/mpfhandler, 有如下优化
- 添加了intervel支持
- 支持备份自动清理
- 使用MMAP优化了性能

# 性能基准
8核CPU, 8进程, 100000条长度47字符日志测试, 相比TimedRotatingFileHandler大约有25%-30%性能损耗

随着进程数增大, 锁竞争也变激烈了, 性能损耗也会进一步增大, 100进程下会有50%-60%性能损耗

8进程, QPS情况
- MultProcTimedRotatingFileHandler: 23482
- TimedRotatingFileHandler: 30349


# 配置示例
```
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(levelname)s %(asctime)s %(name)s %(lineno)d %(process)d %(thread)d] %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'backend_file':{
            'class': 'mptrfhandler.MultProcTimedRotatingFileHandler',
            'filename': 'main.log',
            'when': 'H',  # 按小时滚动
            'backupCount': 10,                                   #备份份数
            'formatter':'verbose',                              #使用哪种formatters日志格式
            'level': 'DEBUG',
            'delay': True,
        },
    },
    'loggers': {
        '': {
            'handlers': ['backend_file'],
            'level': "INFO",
            'propagate': False,
        },
    },
}

logging.config.dictConfig(LOGGING_CONFIG)
```
