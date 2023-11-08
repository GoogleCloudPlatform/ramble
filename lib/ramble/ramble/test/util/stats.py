# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import pytest

import ramble.util.stats


@pytest.mark.parametrize(
    'statistic,input_values,input_units,output',
    [
        (ramble.util.stats.StatsMin(), [-2, 0, 2, 5.5], 's', (-2, 's', 'summary::min')),
        (ramble.util.stats.StatsMax(), [-2, 0, 2, 5.5], 's', (5.5, 's', 'summary::max')),
        (ramble.util.stats.StatsMean(), [-2, 0, 2, 5.5], 's', (1.4, 's', 'summary::mean')),
        (ramble.util.stats.StatsMedian(), [-2, 0, 2, 5.5], 's', (1.0, 's', 'summary::median')),
        (ramble.util.stats.StatsVar(), [-2, 0, 2, 5.5], 's', (10.2, 's^2', 'summary::variance')),
        (ramble.util.stats.StatsVar(), [3], 's', ('variance requires at least two data points',
                                                  '', 'summary::variance')),
        (ramble.util.stats.StatsStdev(), [-2, 0, 2, 5.5], 's', (3.2, 's', 'summary::stdev')),
        (ramble.util.stats.StatsStdev(), [3], 's', ('variance requires at least two data points',
                                                    '', 'summary::stdev')),
        (ramble.util.stats.StatsCountValues(), [-2, 0, 2, 5.5], 's', (4, 'repeats',
                                                                      'summary::n_repeats')),
    ]
)
def test_stats_for_repeat_foms(statistic, input_values, input_units, output):
    assert statistic.report(input_values, input_units) == output
