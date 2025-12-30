from ramble.schema.experiment import experiment_schema_version
from ramble.schema.fom import fom_schema_version
from ramble.schema.metadata import metadata_schema_version

db_schema_version = (
    f"fom-{fom_schema_version}_experiment-{experiment_schema_version}"
    f"_metadata-{metadata_schema_version}"
)
