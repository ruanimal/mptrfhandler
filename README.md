# MultProcTimedRotatingFileHandler
支持按时间滚动的Python多进程日志Handler, 只在python3.5上测试通过
参考了 mpfhandler.MultProcTimedRotatingFileHandler
添加了intervel支持
支持备份自动清理

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
