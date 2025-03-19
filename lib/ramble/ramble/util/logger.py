# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import llnl.util.tty as tty
import llnl.util.tty.log
import llnl.util.tty.color

from contextlib import contextmanager
from pathlib import Path


class Logger:
    """Logger class

    This class providers additional functionality on top of LLNL's tty utility.
    Namely, this class provides a stack of log files, and allows errors to be
    printed to all log files instead of only one.
    """

    def __init__(self):
        """Construct a a logger instance

        A logger instance consists of a stack of logs (self.log_stack) and an
        enabled flag.

        If the enabled flag is set to False, the logger will only print to
        screen instead of to underlying files.
        """
        self.log_stack = []
        self.enabled = True

    def add_log(self, path):
        """Add a log to the current log stack

        Opens (with 'a+' permissions) the file provided by the 'path' argument,
        and stores both the path, and the opened stream object in the current stack
        in the active position.

        Args:
            path: File path for the new log file
        """
        if isinstance(path, str) and self.enabled:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            stream = llnl.util.tty.log.Unbuffered(open(path, "a+"))
            self.log_stack.append((path, stream))

    def remove_log(self):
        """Remove the active stack

        Pop the active log from the log stack, and close the log stream.
        """
        if self.enabled:
            last_log = self.log_stack.pop()
            last_log[1].close()

    def active_log(self):
        """Return the path for the active log

        If any logs are in the log stack, return the filepath of the active log.
        Otherwise, return the string 'stdout'
        """
        if len(self.log_stack) > 0:
            return self.log_stack[-1][0]
        return "stdout"

    def active_stream(self):
        """Return the stream for the active log

        If any logs are in the log stack, return the stream object of the active log.
        Otherwise, return None to indicate the system is handling printing.
        """
        if len(self.log_stack) > 0:
            return self.log_stack[-1][1]
        return None

    def _stream_kwargs(self, default_kwargs=None, index=None):
        """Construct keyword arguments for a stream

        Build keyword arguments of the form: {'stream': <log_stream>} to allow
        LLNL's tty utility to print to a specific stream.

        When default_kwargs are passed in, these are applied on top of the
        constructed kwargs.

        When index is passed in, the stream added into kwargs is the log in
        position index within the stack (where -1 is considered active).

        Args:
            default_kwargs: Default keyword arguments to use
            index: Index of log (in stack) to build kwargs for

        Returns:
            kwargs: Constructed kwargs with defaults applied
        """
        if default_kwargs is None:
            default_kwargs = {}
        kwargs = {}
        stream_index = None
        if index is not None:
            if index >= 0 and index <= len(self.log_stack):
                stream_index = index
            else:
                tty.die(
                    f"Error: Requested stream index of {index} is outside of "
                    f"the stream range of 0 - {len(self.log_stack)}"
                )

        else:
            if len(self.log_stack) > 0:
                stream_index = len(self.log_stack) - 1

        if stream_index is not None:
            kwargs["stream"] = self.log_stack[stream_index][1]

        kwargs.update(default_kwargs)

        return kwargs

    @contextmanager
    def configure_colors(self, **kwargs):
        old_value = llnl.util.tty.color.get_color_when()
        if "stream" in kwargs:
            llnl.util.tty.color.set_color_when("never")
        yield
        llnl.util.tty.color.set_color_when(old_value)

    def all_msg(self, *args, **kwargs):
        """Print a message to all logs

        Pass all args and kwargs to tty.info (which will concatenate and
        print). Perform this action for all logs and the default log (to
        screen).
        """
        for idx, _ in enumerate(self.log_stack):
            st_kwargs = self._stream_kwargs(default_kwargs=kwargs, index=idx)
            with self.configure_colors(**st_kwargs):
                tty.info(*args, **st_kwargs)

        tty.msg(*args, **kwargs)

    def msg(self, *args, **kwargs):
        """Print a message to the active log

        Pass all args and kwargs to tty.info (which will concatenate and
        print). Perform this action for the active log only.
        """
        st_kwargs = self._stream_kwargs(default_kwargs=kwargs)
        with self.configure_colors(**st_kwargs):
            tty.info(*args, **st_kwargs)

    def info(self, *args, **kwargs):
        """Print a message to the active log

        Pass all args and kwargs to tty.info (which will concatenate and
        print). Perform this action for the active log only.
        """
        st_kwargs = self._stream_kwargs(default_kwargs=kwargs)
        with self.configure_colors(**st_kwargs):
            tty.info(*args, **st_kwargs)

    def verbose(self, *args, **kwargs):
        """Print a verbose message to the active log

        Pass all args and kwargs to tty.verbose (which will concatenate and
        print). Perform this action for the active log only.
        """
        st_kwargs = self._stream_kwargs(default_kwargs=kwargs)
        with self.configure_colors(**st_kwargs):
            tty.verbose(*args, **st_kwargs)

    def warn(self, *args, **kwargs):
        """Print a warning message to the active log

        Pass all args and kwargs to tty.warn (which will concatenate and
        print). Perform this action for the active log only.
        """
        st_kwargs = self._stream_kwargs(default_kwargs=kwargs)
        if "stream" in st_kwargs:
            with self.configure_colors(**st_kwargs):
                tty.warn(*args, **st_kwargs)

        tty.warn(*args, **kwargs)

    def debug(self, *args, **kwargs):
        """Print a debug message to the active log

        Pass all args and kwargs to tty.debug (which will concatenate and
        print). Perform this action for the active log only.
        """
        if tty._debug:
            st_kwargs = self._stream_kwargs(default_kwargs=kwargs)
            with self.configure_colors(**st_kwargs):
                tty.debug(*args, **st_kwargs)

    def error(self, *args, **kwargs):
        """Print an error message

        Pass all args and kwargs to tty.error (which will concatenate and
        print). Perform this action all logs, and the default stream (print to
        screen).
        """
        for idx, _ in enumerate(self.log_stack):
            st_kwargs = self._stream_kwargs(index=idx, default_kwargs=kwargs)
            with self.configure_colors(**st_kwargs):
                tty.error(*args, **st_kwargs)

        tty.error(*args, **kwargs)

    def die(self, *args, **kwargs):
        """Print an error message and terminate execution

        Pass all args and kwargs to tty.error (which will concatenate and
        print). Perform this action all logs. After all logs are printed to,
        terminate execution (and error) using tty.die.
        """
        for idx, _ in enumerate(self.log_stack):
            st_kwargs = self._stream_kwargs(index=idx, default_kwargs=kwargs)
            with self.configure_colors(**st_kwargs):
                tty.error(*args, **st_kwargs)

        while self.log_stack:
            self.remove_log()

        tty.die(*args, **kwargs)


logger = Logger()
