from functools import wraps
import time


def log_inout(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            args[0].logger.debug('[START] {0}'.format(func.__name__))
            func(*args, **kwargs)
            args[0].logger.debug('[END] {0}'.format(func.__name__))
        except Exception as e:
            func(*args, **kwargs)
    return wrapper


def timeit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            t0 = time.time()
            func(*args, **kwargs)
            et = time.time() - t0
            args[0].logger.debug('[TIMEIT] {0} took {1:.4f} seconds'.format(func.__name__, et))
        except Exception as e:
            func(*args, **kwargs)
    return wrapper


if __name__ == "__main__":
    import logging

    logger = logging.getLogger()
    logger.setLevel("DEBUG")
    handler = logging.StreamHandler()
    log_format = "%(asctime)s %(levelname)s -- %(message)s"
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    class A(object):

        def __init__(self):
            self.logger = logging.getLogger(self.__class__.__name__)

        @log_inout
        @timeit
        def func(self, st):
            time.sleep(st)

    c = A()
    c.func(2)
