.. Copyright 2022-2025 The Ramble Authors

   Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
   https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
   <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
   option. This file may not be copied, modified, or distributed
   except according to those terms.

Execute Experiments
-------------------

Now that you have made the appropriate modifications, set up, execute, and
analyze the new experiments using:

.. code-block:: console

    $ ramble workspace setup
    $ ramble on
    $ ramble workspace analyze

This creates a ``results`` file in the root of the workspace that contains
extracted figures of merit. If the experiments were successful, this file will
show the following results:

* Core Time: CPU time (in seconds) spent on the benchmark calculations
* Wall Time: Elapsed real time (in seconds) spent on the benchmark calculations
* Percent Core Time: Core Time / Wall Time
* Nanosecs per day: Nanoseconds of simulation per day at the speed achieved
* Hours per nanosec: Hours required to calculate 1 nanosecond of simulation at
  the speed achieved
