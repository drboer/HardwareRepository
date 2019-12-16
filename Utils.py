from functools import wraps
import time


def log_inout(func):
    @wraps(func)
    def wrapper(cls):
        try:
            cls.logger.debug('[START] {0}'.format(func.__name__))
            func(cls)
            cls.logger.debug('[END] {0}'.format(func.__name__))
        except Exception as e:
            func(cls)
    return wrapper


def timeit(func):
    @wraps(func)
    def wrapper(cls):
        try:
            t0 = time.time()
            func(cls)
            et = time.time() - t0
            cls.logger.debug('[TIMEIT] {0} took {1:.4f} seconds'.format(func.__name__, et))
        except Exception as e:
            func(cls)
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
        def func(self):
            time.sleep(2)

    c = A()
    c.func()
