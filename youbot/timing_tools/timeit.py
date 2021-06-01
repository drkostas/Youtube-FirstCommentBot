from contextlib import ContextDecorator
from typing import Callable, IO
from functools import wraps
from time import time

from youbot import ColorizedLogger

time_logger = ColorizedLogger('Timeit', 'white')


class timeit(ContextDecorator):
    custom_print: str
    skip: bool
    file: IO

    def __init__(self, **kwargs):
        """Decorator/ContextManager for counting the execution times of functions and code blocks

        Args:
            custom_print: Custom print string Use {duration} to reference the running time.
                          When used as decorator it can also be formatted using
                          `func_name`, `args`, and {0}, {1}, .. to reference the function's
                          first, second, ... argument.
            skip: If True, don't time this time. Suitable when inside loops
            file: Write the timing output to a file too
        """

        self.total = None
        self.skip = False
        self.internal_only = False
        self.__dict__.update(kwargs)

    def __call__(self, func: Callable):
        """ This is called only when invoked as a decorator

        Args:
            func: The method to wrap
        """

        @wraps(func)
        def timed(*args, **kwargs):
            with self._recreate_cm():
                self.func_name = func.__name__
                self.args = args
                self.kwargs = kwargs
                self.all_args = (*args, *kwargs.values()) if kwargs != {} else args
                return func(*args, **kwargs)

        return timed

    def __enter__(self, *args, **kwargs):
        if not self.skip:
            self.ts = time()
        return self

    def __exit__(self, type, value, traceback):
        if self.skip:
            return

        self.te = time()
        self.total = self.te - self.ts
        if hasattr(self, 'func_name'):
            if not hasattr(self, 'custom_print'):
                print_string = 'Func: {func_name!r} with args: {args!r} took: {duration:2.5f} sec(s)'
            else:
                print_string = self.custom_print
            time_logger.info(print_string.format(*self.args, func_name=self.func_name,
                                                 args=self.all_args,
                                                 duration=self.total,
                                                 **self.kwargs))
        else:
            if not hasattr(self, 'custom_print'):
                print_string = 'Code block took: {duration:2.5f} sec(s)'
            else:
                print_string = self.custom_print
            if hasattr(self, 'file'):
                self.file.write(print_string.format(duration=self.total))
            if not self.internal_only:
                time_logger.info(print_string.format(duration=self.total))
