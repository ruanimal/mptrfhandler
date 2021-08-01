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
            'class': 'mptrfhandler.MultProcTimedRotatingFileHandler',
            'filename': 'main.log',
            # 'backupCount': 5,
            'formatter':'simple',
            'when': 'S',
            # 'debug': True,
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
import random
from multiprocessing import Pool


logging.config.dictConfig(LOGGING)

random.seed(os.getpid())
print(os.getpid())

def log_msg(msg):
    # time.sleep(random.random()/30)
    logging.info('%s\t%s', msg, os.getpid())

def test_file():
    res = 0
    for name in os.listdir():
        if name.startswith('main.log'):
            for line in open(name):
                res += int(line.split('\t')[1])
    print('jobs sum: ', res)
    assert res == sum(range(JOBS))

if __name__ == '__main__':
    os.system('rm -rf main.log.*')
    os.system('rm -rf .main.lock*')
    os.system('truncate -s0 main.log')
    time.sleep(1)

    JOBS = 100000
    WORKERS = 100
    pool = Pool(WORKERS)
    start = time.time()
    pool.map(log_msg, ('{:0>10}'.format(i) for i in range(JOBS)))
    pool.close()
    pool.join()
    print('QPS:', JOBS/(time.time()-start))
    time.sleep(2)
    test_file()
