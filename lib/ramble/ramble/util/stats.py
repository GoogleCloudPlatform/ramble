# Copyright 2022-2025 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import math
import statistics

from scipy.stats import t


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
    name = ""

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


class StatsHarmonicMean(StatsBase):
    name = "harmonic_mean"

    def compute(self, values):
        try:
            return round(statistics.harmonic_mean(values), max_decimal_places(values))
        except statistics.StatisticsError:
            return "NA"


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


def _calculate_margin_of_error(values, confidence_level):
    """Calculates the margin of error for a given confidence interval."""
    n = len(values)
    stdev = statistics.stdev(values)

    # For small sample sizes (n < 30), a t-distribution is more accurate.
    # For larger samples, the z-score is a good approximation.
    if n < 30:
        degrees_freedom = n - 1
        t_score = float(t.ppf(1 - (1 - confidence_level) / 2, degrees_freedom))
        return t_score * (stdev / math.sqrt(n))
    else:
        # Using z-score for confidence.
        if confidence_level == 0.99:
            z_score = 2.576
        elif confidence_level == 0.95:
            z_score = 1.96
        elif confidence_level == 0.90:
            z_score = 1.645
        elif confidence_level == 0.50:
            z_score = 0.674
        else:
            z_score = None
        return z_score * (stdev / math.sqrt(n))


class StatsConfidenceIntervalLower99(StatsBase):
    name = "ci_99_lower"
    min_count = 2

    def compute(self, values):
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.99)
        return round(mean - margin_of_error, max_decimal_places(values))


class StatsConfidenceIntervalUpper99(StatsBase):
    name = "ci_99_upper"
    min_count = 2

    def compute(self, values):
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.99)
        return round(mean + margin_of_error, max_decimal_places(values))


class StatsConfidenceIntervalLower95(StatsBase):
    name = "ci_95_lower"
    min_count = 2

    def compute(self, values):
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.95)
        return round(mean - margin_of_error, max_decimal_places(values))


class StatsConfidenceIntervalUpper95(StatsBase):
    name = "ci_95_upper"
    min_count = 2

    def compute(self, values):
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.95)
        return round(mean + margin_of_error, max_decimal_places(values))


class StatsConfidenceIntervalLower90(StatsBase):
    name = "ci_90_lower"
    min_count = 2

    def compute(self, values):
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.90)
        return round(mean - margin_of_error, max_decimal_places(values))


class StatsConfidenceIntervalUpper90(StatsBase):
    name = "ci_90_upper"
    min_count = 2

    def compute(self, values):
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.90)
        return round(mean + margin_of_error, max_decimal_places(values))


class StatsConfidenceIntervalLower50(StatsBase):
    name = "ci_50_lower"
    min_count = 2

    def compute(self, values):
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.50)
        return round(mean - margin_of_error, max_decimal_places(values))


class StatsConfidenceIntervalUpper50(StatsBase):
    name = "ci_50_upper"
    min_count = 2

    def compute(self, values):
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.50)
        return round(mean + margin_of_error, max_decimal_places(values))


all_stats = [
    StatsMin(),
    StatsMax(),
    StatsMean(),
    StatsHarmonicMean(),
    StatsMedian(),
    StatsVar(),
    StatsStdev(),
    StatsCoefficientOfVariation(),
    StatsConfidenceIntervalLower99(),
    StatsConfidenceIntervalUpper99(),
    StatsConfidenceIntervalLower95(),
    StatsConfidenceIntervalUpper95(),
    StatsConfidenceIntervalLower90(),
    StatsConfidenceIntervalUpper90(),
    StatsConfidenceIntervalLower50(),
    StatsConfidenceIntervalUpper50(),
]
