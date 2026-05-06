# Copyright 2022-2026 The Ramble Authors
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

from ramble.schema.experiment import experiment_schema_version
from ramble.schema.experiments_metadata import experiments_metadata_schema_version
from ramble.schema.fom import fom_schema_version
from ramble.schema.metadata import metadata_schema_version
from ramble.schema.software_db import software_db_schema_version

db_schema_version = (
    f"fom-{fom_schema_version}"
    f"_experiment-{experiment_schema_version}"
    f"_metadata-{metadata_schema_version}"
    f"_experiments-metadata-{experiments_metadata_schema_version}"
    f"_software-{software_db_schema_version}"
)
