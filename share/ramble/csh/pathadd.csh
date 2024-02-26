# Copyright 2022-2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

########################################################################
# Prepends directories to path, if they exist.
#      pathadd /path/to/dir            # add to PATH
# or   pathadd OTHERPATH /path/to/dir  # add to OTHERPATH
########################################################################
# If no variable name is supplied, just append to PATH
# otherwise append to that variable.
set _pa_varname = PATH;
set _pa_new_path = $_pa_args[1];

if ($#_pa_args > 1) then
    set _pa_varname = $_pa_args[1]
    set _pa_new_path = $_pa_args[2]
endif

# Check whether the variable is set yet.
set _pa_old_value = ""
eval set _pa_set = '$?'$_pa_varname
if ($_pa_set == 1) then
    eval set _pa_old_value='$'$_pa_varname
endif

# Do the actual prepending here, if it is a dir and not already in the path
if ( -d $_pa_new_path && \:$_pa_old_value\: !~ *\:$_pa_new_path\:* ) then
    if ("x$_pa_old_value" == "x") then
        setenv $_pa_varname $_pa_new_path
    else
        setenv $_pa_varname $_pa_new_path\:$_pa_old_value
    endif
endif

unset _pa_args _pa_new_path _pa_old_value _pa_set _pa_varname
