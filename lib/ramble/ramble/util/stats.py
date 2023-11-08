# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import statistics


def decimal_places(value):
    """Returns the number of decimal places of a value"""

    val_str = str(value)
    if '.' not in val_str:
        return 0
    else:
        return len(val_str.split('.')[1])


def max_decimal_places(list):
    """Returns the max decimal places of a list of values"""

    max = 0
    for val in list:
        if decimal_places(val) > max:
            max = decimal_places(val)
    return max


class StatsBase(object):
    def compute(self, values):
        pass

    def report(self, values, units):
        return (self.compute(values), units, f'summary::{self.name}')


class StatsMin(StatsBase):
    name = 'min'

    def compute(self, values):
        return min(values)


class StatsMax(StatsBase):
    name = 'max'

    def compute(self, values):
        return max(values)


class StatsMean(StatsBase):
    name = 'mean'

    def compute(self, values):
        return round(statistics.mean(values), max_decimal_places(values))


class StatsMedian(StatsBase):
    name = 'median'

    def compute(self, values):
        return round(statistics.median(values), max_decimal_places(values))


class StatsVar(StatsBase):
    name = 'variance'

    def compute(self, values):
        return round(statistics.variance(values), max_decimal_places(values))

    def report(self, values, units):
        var = ''
        new_units = ''

        try:
            var = self.compute(values)
            new_units = f'{units}^2'
        except statistics.StatisticsError as e:
            var = str(e)
            new_units = ''

        return (var, new_units, f'summary::{self.name}')


class StatsStdev(StatsBase):
    name = 'stdev'

    def compute(self, values):
        return round(statistics.stdev(values), max_decimal_places(values))

    def report(self, values, units):
        var = ''
        new_units = ''

        try:
            var = self.compute(values)
            new_units = units
        except statistics.StatisticsError as e:
            var = str(e)
            new_units = ''

        return (var, new_units, f'summary::{self.name}')


class StatsCountValues(StatsBase):
    name = 'n_successful_repeats'

    def compute(self, values):
        return len(values)

    def report(self, values, units):
        return (self.compute(values), 'repeats', f'summary::{self.name}')


all_stats = [StatsMin(),
             StatsMax(),
             StatsMean(),
             StatsMedian(),
             StatsVar(),
             StatsStdev(),
             StatsCountValues()]
