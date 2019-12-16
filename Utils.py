from functools import wraps
# import logging
#
# logger = logging.getLogger()
# logger.setLevel("DEBUG")
# handler = logging.StreamHandler()
# log_format = "%(asctime)s %(levelname)s -- %(message)s"
# formatter = logging.Formatter(log_format)
# handler.setFormatter(formatter)
# logger.addHandler(handler)


def fmt_logger(func):
    @wraps(func)
    def wrapper(cls):
        cls.logger.debug('[START] {0}'.format(func.__name__))
        func(cls)
        cls.logger.debug('[END] {0}'.format(func.__name__))
    return wrapper


# class Collect(object):
#
#     def __init__(self):
#         self.logger = logging.getLogger(self.__class__.__name__)
#
#     @fmt_logger
#     def method(self):
#         self.logger.debug("this is the collect method")
#
#
# if __name__ == "__main__":
#     c = Collect()
#     c.method()
