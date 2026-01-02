# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import decimal
import math
import statistics
from typing import List, Tuple, Union

from scipy.stats import t

NA = "NA"


def _decimal_places(value: float) -> int:
    """Returns the number of decimal places of a value"""
    d = decimal.Decimal(str(value))
    exponent = d.as_tuple().exponent
    if not isinstance(exponent, int):
        raise ValueError(f"Invalid decimal value {value}")
    return -exponent


def _max_decimal_places(values: List[float]) -> int:
    """Returns the max decimal places of a list of values"""
    return max(_decimal_places(v) for v in values)


class StatsBase:
    min_count: int = 1
    name: str = ""

    def compute(self, values: List[float]) -> Union[float, str]:
        raise NotImplementedError

    def get_unit(self, unit: str) -> str:
        return unit

    def report(self, values: List[float], unit: str) -> Tuple[Union[float, str], str, str]:
        label = f"summary::{self.name}"
        if len(values) < self.min_count:
            return (NA, "", label)
        return (self.compute(values), self.get_unit(unit), label)


class StatsMin(StatsBase):
    name = "min"

    def compute(self, values: List[float]) -> float:
        return min(values)


class StatsMax(StatsBase):
    name = "max"

    def compute(self, values: List[float]) -> float:
        return max(values)


class StatsMean(StatsBase):
    name = "mean"

    def compute(self, values: List[float]) -> float:
        return round(statistics.mean(values), _max_decimal_places(values))


class StatsHarmonicMean(StatsBase):
    name = "harmonic_mean"

    def compute(self, values: List[float]) -> Union[float, str]:
        try:
            return round(statistics.harmonic_mean(values), _max_decimal_places(values))
        except statistics.StatisticsError:
            return NA


class StatsMedian(StatsBase):
    name = "median"

    def compute(self, values: List[float]) -> float:
        return round(statistics.median(values), _max_decimal_places(values))


class StatsVar(StatsBase):
    name = "variance"
    min_count = 2

    def get_unit(self, unit: str) -> str:
        return f"{unit}^2"

    def compute(self, values: List[float]) -> float:
        return round(statistics.variance(values), _max_decimal_places(values))


class StatsStdev(StatsBase):
    name = "stdev"
    min_count = 2

    def compute(self, values: List[float]) -> float:
        return round(statistics.stdev(values), _max_decimal_places(values))


class StatsCoefficientOfVariation(StatsBase):
    name = "cv"
    min_count = 2

    def compute(self, values: List[float]) -> Union[float, str]:
        mean = statistics.mean(values)
        # Only guard against zero mean.
        # While CV isn\'t particularly meaningful when negative values are present,
        # calculate anyway and leave the interpretation to individual experiments.
        if not mean:
            return NA
        return round(
            statistics.stdev(values) / statistics.mean(values), _max_decimal_places(values)
        )

    def get_unit(self, unit: str) -> str:
        # `unit` unused
        del unit
        return ""


def _calculate_margin_of_error(values: List[float], confidence_level: float) -> float:
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
            raise ValueError("Unsupported confidence level")
        return z_score * (stdev / math.sqrt(n))


class StatsConfidenceIntervalLower99(StatsBase):
    name = "ci_99_lower"
    min_count = 2

    def compute(self, values: List[float]) -> float:
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.99)
        return round(mean - margin_of_error, _max_decimal_places(values))


class StatsConfidenceIntervalUpper99(StatsBase):
    name = "ci_99_upper"
    min_count = 2

    def compute(self, values: List[float]) -> float:
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.99)
        return round(mean + margin_of_error, _max_decimal_places(values))


class StatsConfidenceIntervalLower95(StatsBase):
    name = "ci_95_lower"
    min_count = 2

    def compute(self, values: List[float]) -> float:
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.95)
        return round(mean - margin_of_error, _max_decimal_places(values))


class StatsConfidenceIntervalUpper95(StatsBase):
    name = "ci_95_upper"
    min_count = 2

    def compute(self, values: List[float]) -> float:
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.95)
        return round(mean + margin_of_error, _max_decimal_places(values))


class StatsConfidenceIntervalLower90(StatsBase):
    name = "ci_90_lower"
    min_count = 2

    def compute(self, values: List[float]) -> float:
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.90)
        return round(mean - margin_of_error, _max_decimal_places(values))


class StatsConfidenceIntervalUpper90(StatsBase):
    name = "ci_90_upper"
    min_count = 2

    def compute(self, values: List[float]) -> float:
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.90)
        return round(mean + margin_of_error, _max_decimal_places(values))


class StatsConfidenceIntervalLower50(StatsBase):
    name = "ci_50_lower"
    min_count = 2

    def compute(self, values: List[float]) -> float:
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.50)
        return round(mean - margin_of_error, _max_decimal_places(values))


class StatsConfidenceIntervalUpper50(StatsBase):
    name = "ci_50_upper"
    min_count = 2

    def compute(self, values: List[float]) -> float:
        mean = statistics.mean(values)
        margin_of_error = _calculate_margin_of_error(values, 0.50)
        return round(mean + margin_of_error, _max_decimal_places(values))


all_stats = [
    StatsMin(),
    StatsMax(),
    StatsMean(),
    StatsHarmonicMean(),
    StatsMedian(),
    StatsVar(),
    StatsStdev(),
    StatsCoefficientOfVariation(),
    StatsConfidenceIntervalUpper99(),
    StatsConfidenceIntervalUpper95(),
    StatsConfidenceIntervalUpper90(),
    StatsConfidenceIntervalUpper50(),
    StatsConfidenceIntervalLower50(),
    StatsConfidenceIntervalLower90(),
    StatsConfidenceIntervalLower95(),
    StatsConfidenceIntervalLower99(),
]
