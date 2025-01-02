# Copyright 2022-2025 The Ramble Authors
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
    if "." not in val_str:
        return 0
    else:
        return len(val_str.split(".")[1])


def max_decimal_places(list):
    """Returns the max decimal places of a list of values"""

    max = 0
    for val in list:
        if decimal_places(val) > max:
            max = decimal_places(val)
    return max


class StatsBase:
    min_count = 1

    def compute(self, values):
        pass

    def get_unit(self, unit):
        return unit

    def report(self, values, unit):
        label = f"summary::{self.name}"
        if len(values) < self.min_count:
            return ("NA", "", label)
        return (self.compute(values), self.get_unit(unit), label)


class StatsMin(StatsBase):
    name = "min"

    def compute(self, values):
        return min(values)


class StatsMax(StatsBase):
    name = "max"

    def compute(self, values):
        return max(values)


class StatsMean(StatsBase):
    name = "mean"

    def compute(self, values):
        return round(statistics.mean(values), max_decimal_places(values))


class StatsMedian(StatsBase):
    name = "median"

    def compute(self, values):
        return round(statistics.median(values), max_decimal_places(values))


class StatsVar(StatsBase):
    name = "variance"
    min_count = 2

    def get_unit(self, unit):
        return f"{unit}^2"

    def compute(self, values):
        return round(statistics.variance(values), max_decimal_places(values))


class StatsStdev(StatsBase):
    name = "stdev"
    min_count = 2

    def compute(self, values):
        return round(statistics.stdev(values), max_decimal_places(values))


class StatsCoefficientOfVariation(StatsBase):
    name = "cv"
    min_count = 2

    def compute(self, values):
        mean = statistics.mean(values)
        # Only guard against zero mean.
        # While CV isn't particularly meaningful when negative values are present,
        # calculate anyway and leave the interpretation to individual experiments.
        if not mean:
            return "NA"
        return round(
            statistics.stdev(values) / statistics.mean(values), max_decimal_places(values)
        )

    def get_unit(self, unit):
        # `unit` unused
        del unit
        return ""


all_stats = [
    StatsMin(),
    StatsMax(),
    StatsMean(),
    StatsMedian(),
    StatsVar(),
    StatsStdev(),
    StatsCoefficientOfVariation(),
]
