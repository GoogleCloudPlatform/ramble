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

* Average Timestep Time: Time (in seconds) on average each timestep takes
* Cumulative Timestep Time: Time (in seconds) spent executing all timesteps
* Minimum Timestep Time: Minimum time (in seconds) spent on any one timestep
* Maximum Timestep Time: Maximum time (in seconds) spent on any one timestep
* Number of timesteps: Count of total timesteps performed
* Avg. Max Ratio Time: Ratio of Average Timestep Time and Maximum Timestep Time
