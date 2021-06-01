from contextlib import ContextDecorator
from typing import Callable, IO, List
from io import StringIO
from functools import wraps
import cProfile
import pstats

from youbot import ColorizedLogger

profile_logger = ColorizedLogger('Profileit', 'white')


class profileit(ContextDecorator):
    custom_print: str
    profiler: cProfile.Profile
    stream: StringIO
    sort_by: str
    keep_only_these: List
    fraction: float
    skip: bool
    profiler_output: str
    file: IO

    def __init__(self, **kwargs):
        """Decorator/ContextManager for profiling functions and code blocks

        Args:
            custom_print: Custom print string. When used as decorator it can also be formatted using
                          `func_name`, `args`, and {0}, {1}, .. to reference the function's
                          first, second, ... argument.
            sort_by: pstats sorting column
            profiler_output: Filepath where to save the profiling results (.o file)
            keep_only_these: List of strings - grep on the profiling output and print only lines
                             containing any of these strings
            fraction: pstats.print_stats() fraction argument
            skip: If True, don't time this time. Suitable when inside loops
            file: Write the timing output to a file too
        """

        self.profiler = cProfile.Profile()
        self.stream = StringIO()
        self.sort_by = 'stdname'
        self.keep_only_these = []
        self.fraction = 1.0
        self.skip = False
        self.__dict__.update(kwargs)

    def __call__(self, func: Callable):
        """ This is called only when invoked as a decorator

        Args:
            func: The method to wrap
        """

        @wraps(func)
        def profiled(*args, **kwargs):
            with self._recreate_cm():
                self.func_name = func.__name__
                self.args = args
                self.kwargs = kwargs
                self.all_args = (*args, *kwargs.values()) if kwargs != {} else args
                return func(*args, **kwargs)

        return profiled

    def __enter__(self, *args, **kwargs):
        if not self.skip:
            self.profiler.enable()
        return self

    def __exit__(self, type, value, traceback):
        if self.skip:
            return

        self.profiler.disable()
        ps = pstats.Stats(self.profiler, stream=self.stream).sort_stats(self.sort_by)
        ps.print_stats(self.fraction)

        # If used as a decorator
        if hasattr(self, 'func_name'):
            if not hasattr(self, 'custom_print'):
                print_string = 'Func: {func_name!r} with args: {args!r} profiled:'
            else:
                print_string = self.custom_print
            print_string = print_string.format(*self.args, func_name=self.func_name,
                                               args=self.all_args,
                                               **self.kwargs)
        # If used as contextmanager
        else:
            if not hasattr(self, 'custom_print'):
                print_string = 'Code block profiled:'
            else:
                print_string = self.custom_print

        # Get Profiling results
        prof_res = self.stream.getvalue()
        if len(self.keep_only_these) > 0:
            # Keep only lines containing the specified words
            prof_res_list = [line for line in prof_res.split('\n')
                        if any(keep_word in line for keep_word in self.keep_only_these)]
            prof_res = '\n'.join(prof_res_list)

        # Print to file if requested
        if hasattr(self, 'file'):
            self.file.write(print_string)
            self.file.write("\n%s" % prof_res)

        # Save profiler output to a file if requested
        if hasattr(self, 'profiler_output'):
            self.profiler.dump_stats(self.profiler_output)

        # Actual Print
        profile_logger.info(print_string)
        profile_logger.info("%s", prof_res)
