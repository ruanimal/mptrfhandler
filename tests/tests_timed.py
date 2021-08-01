LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  # 是否禁用已存在的日志记录器
    'formatters': {
        'simple': {
            'format': '[%(asctime)s %(levelname)s]\t%(message)s',
        },
    },
    'handlers': {
        'backend_file':{
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'main.log',
            # 'backupCount': 5,
            'formatter':'simple',
            'when': 'S',
        },
    },
    'loggers': {
        '': {
            'handlers': ['backend_file'],
            'level': 'INFO',
            'propagate': False,
        },
    }
}

import logging
import logging.config
import os
import time
from multiprocessing import Pool


logging.config.dictConfig(LOGGING)

def log_msg(msg):
    logging.info('%s\t%s', msg, os.getpid())

if __name__ == '__main__':
    os.system('rm -rf main.log.*')
    os.system('truncate -s0 main.log')

    JOBS = 100000
    start = time.time()
    for i in ('{:0>10}'.format(i) for i in range(JOBS)):
        log_msg(i)
    print('QPS:', JOBS/(time.time()-start))
