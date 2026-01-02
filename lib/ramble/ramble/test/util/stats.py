# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import math

import pytest

import ramble.util.stats


@pytest.mark.parametrize(
    "statistic,input_values,input_units,output",
    [
        (ramble.util.stats.StatsMin(), [-2, 0, 2, 5.5], "s", (-2, "s", "summary::min")),
        (ramble.util.stats.StatsMax(), [-2, 0, 2, 5.5], "s", (5.5, "s", "summary::max")),
        # Test for scientific notation support
        (ramble.util.stats.StatsMean(), [-2, 0, 2, 5.5, 1.45e1], "s", (4, "s", "summary::mean")),
        (
            ramble.util.stats.StatsHarmonicMean(),
            [2, 3, 5],
            "s",
            (3.0, "s", "summary::harmonic_mean"),
        ),
        (
            ramble.util.stats.StatsHarmonicMean(),
            [2, 3, 5, -1],
            "s",
            ("NA", "s", "summary::harmonic_mean"),
        ),
        (ramble.util.stats.StatsMedian(), [-2, 0, 2, 5.5], "s", (1.0, "s", "summary::median")),
        (ramble.util.stats.StatsVar(), [-2, 0, 2, 5.5], "s", (10.2, "s^2", "summary::variance")),
        (ramble.util.stats.StatsVar(), [3], "s", ("NA", "", "summary::variance")),
        (ramble.util.stats.StatsStdev(), [-2, 0, 2, 5.5], "s", (3.2, "s", "summary::stdev")),
        (ramble.util.stats.StatsStdev(), [3], "s", ("NA", "", "summary::stdev")),
        (ramble.util.stats.StatsCoefficientOfVariation(), [3], "s", ("NA", "", "summary::cv")),
        (ramble.util.stats.StatsCoefficientOfVariation(), [3, -3], "s", ("NA", "", "summary::cv")),
        (
            ramble.util.stats.StatsCoefficientOfVariation(),
            [6.79, 5.6, 4.31, 5.5],
            "s",
            (0.18, "", "summary::cv"),
        ),
        (
            ramble.util.stats.StatsConfidenceIntervalLower95(),
            [1, 2, 3, 4, 5],
            "s",
            (1.0, "s", "summary::ci_95_lower"),
        ),
        (
            ramble.util.stats.StatsConfidenceIntervalUpper95(),
            [1, 2, 3, 4, 5],
            "s",
            (5.0, "s", "summary::ci_95_upper"),
        ),
        (
            ramble.util.stats.StatsConfidenceIntervalLower95(),
            [1],
            "s",
            ("NA", "", "summary::ci_95_lower"),
        ),
        (
            ramble.util.stats.StatsConfidenceIntervalUpper95(),
            [1],
            "s",
            ("NA", "", "summary::ci_95_upper"),
        ),
        # Test case with a larger sample size to verify z-score approximation
        (
            ramble.util.stats.StatsConfidenceIntervalLower95(),
            list(range(1, 31)),
            "s",
            (12.0, "s", "summary::ci_95_lower"),
        ),
        (
            ramble.util.stats.StatsConfidenceIntervalUpper95(),
            list(range(1, 31)),
            "s",
            (19.0, "s", "summary::ci_95_upper"),
        ),
        (
            ramble.util.stats.StatsConfidenceIntervalLower99(),
            list(range(1, 31)),
            "s",
            (11.0, "s", "summary::ci_99_lower"),
        ),
        (
            ramble.util.stats.StatsConfidenceIntervalUpper99(),
            list(range(1, 31)),
            "s",
            (20.0, "s", "summary::ci_99_upper"),
        ),
        (
            ramble.util.stats.StatsConfidenceIntervalLower90(),
            list(range(1, 31)),
            "s",
            (13.0, "s", "summary::ci_90_lower"),
        ),
        (
            ramble.util.stats.StatsConfidenceIntervalUpper90(),
            list(range(1, 31)),
            "s",
            (18.0, "s", "summary::ci_90_upper"),
        ),
        (
            ramble.util.stats.StatsConfidenceIntervalLower50(),
            list(range(1, 31)),
            "s",
            (14.0, "s", "summary::ci_50_lower"),
        ),
        (
            ramble.util.stats.StatsConfidenceIntervalUpper50(),
            list(range(1, 31)),
            "s",
            (17.0, "s", "summary::ci_50_upper"),
        ),
    ],
)
def test_stats_for_repeat_foms(statistic, input_values, input_units, output):
    assert statistic.report(input_values, input_units) == output


def test_calculate_margin_of_error():
    data = [
        3.71,
        4.28,
        6.93,
        5.07,
        5.60,
        5.45,
        4.57,
        5.05,
        4.78,
        5.48,
        4.89,
        5.65,
        8.25,
        6.28,
        6.38,
        6.82,
        2.79,
        4.65,
        4.18,
        4.69,
        5.90,
        5.64,
        4.05,
        5.33,
        3.85,
        4.37,
        5.03,
        6.72,
        4.33,
        4.77,
    ]

    assert math.isclose(
        ramble.util.stats._calculate_margin_of_error(data, 0.99), 0.531, abs_tol=1e-3
    )
    assert math.isclose(
        ramble.util.stats._calculate_margin_of_error(data, 0.95), 0.404, abs_tol=1e-3
    )
    assert math.isclose(
        ramble.util.stats._calculate_margin_of_error(data, 0.90), 0.339, abs_tol=1e-3
    )
    assert math.isclose(
        ramble.util.stats._calculate_margin_of_error(data, 0.50), 0.139, abs_tol=1e-3
    )
    with pytest.raises(ValueError, match="Unsupported confidence level"):
        ramble.util.stats._calculate_margin_of_error(data, 0.1)
