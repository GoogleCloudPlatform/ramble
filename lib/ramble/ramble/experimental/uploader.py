# Copyright 2022-2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license
# <LICENSE-MIT or https://opensource.org/licenses/MIT>, at your
# option. This file may not be copied, modified, or distributed
# except according to those terms.

import llnl.util.tty as tty
import json
import sys
import math


default_node_type_val = "Not Specified"


class Uploader():
    # TODO: should the class store the base uri?
    def perform_upload(self, uri, workspace_name, data):
        # TODO: move content checking to __init__ ?
        if not uri:
            raise ValueError(
                "%s requires %s argument." % (self.__class__, uri))
        if not data:
            raise ValueError(
                "%s requires %s argument." % (self.__class__, data))
        pass


class Experiment():
    """
    Class representation of experiment data
    """
    def __init__(self, name, data, timestamp):
        self.name = name
        self.foms = []
        self.id = None  # This is essentially the hash
        self.data = data
        self.application_name = data['RAMBLE_VARIABLES']['application_name']
        self.workspace_name = data['RAMBLE_VARIABLES']['workspace_name']
        self.workload_name = data['RAMBLE_VARIABLES']['workload_name']
        self.bulk_hash = None  # proxy for workspace or "uploaded with"
        self.n_nodes = data['RAMBLE_VARIABLES']['n_nodes']
        self.processes_per_node = data['RAMBLE_VARIABLES']['processes_per_node']
        self.n_ranks = data['RAMBLE_VARIABLES']['n_ranks']
        self.n_threads = data['RAMBLE_VARIABLES']['n_threads']
        self.node_type = default_node_type_val

        # FIXME: this is no longer strictly needed since it is just a concat of known properties
        exps_hash = "{workspace_name}::{application}::{workload}::{date}".format(
            workspace_name=self.workspace_name,
            application=self.application_name,
            workload=self.workload_name,
            date=timestamp
        )

        self.bulk_hash = exps_hash

        self.timestamp = str(timestamp)

        self.id = None
        self.generate_hash()

    def generate_hash(self):
        # Avoid regenerating a hash when possible
        # (The hash of an object must never change during its lifetime..)
        if self.id is None:
            #  TODO: this might be better as a hash of something we intuitively
            # expect to be uniqie, like:
            # "{RAMBLE_STATUS}-{application_name}-{experiment_name}-{time}-etc"
            # If we don't want this, we can go back to this class just being a dict
            self.id = hash(self)
        return self.id

    def get_hash(self):
        return self.generate_hash()

    def to_json(self):

        # deep copy so the assignment below doesn't affect the foms array
        import copy
        j = copy.deepcopy(self.__dict__)

        j['foms'] = json.dumps(self.foms)
        j['data'] = json.dumps(self.data)
        return j


def determine_node_type(experiment, contexts):
    """
    Extract node type from available FOMS.

    First prio is machine specific data, such as GCP meta data
    Second prio is more general data like CPU type
    """
    for context in contexts:
        for fom in context['foms']:
            if 'machine-type' in fom['name']:
                experiment.node_type = fom['value']
                continue
            elif 'Model name' in fom['name']:
                experiment.node_type = fom['value']
                continue

        # Termination condition
        if experiment.node_type != default_node_type_val:
            continue


def format_data(data_in):
    """
    Goal: convert results to a more searchable and decomposed format for insertion
    into data store (etc)

    Input:

    .. code-block:: text

        { expierment_name:
            { "CONTEXTS": {
                "context_name": "FOM_name { unit: "value", "value":value" }
            ...}
            }
        }

    Output: The general idea is the decompose the results into a more "database"
    like format, where the runs and FOMs are in a different table.
    """
    tty.debug("Format Data in")
    tty.debug(data_in)
    results = []

    # TODO: what is the nice way to deal with the distinction between
    # numberic/float and string FOM values

    from datetime import datetime
    current_dateTime = datetime.now()

    for exp in data_in['experiments']:
        if exp['RAMBLE_STATUS'] == 'SUCCESS':
            e = Experiment(exp['name'], exp, current_dateTime)
            results.append(e)
            # experiment_id = exp.hash()
            # 'experiment_id': experiment_id,
            for context in exp['CONTEXTS']:
                for fom in context['foms']:
                    # TODO: check on value to make sure it's a number
                    e.foms.append(
                        {
                            'name': fom['name'],
                            'value': fom['value'],
                            'unit': fom['units'],
                            'context': context['name'],
                        }
                    )

            # Explicitly try to pull out node type, if the run provided enough data
            determine_node_type(e, exp['CONTEXTS'])

    return results


class BigQueryUploader(Uploader):
    """Class to handle upload of FOMs to BigQuery
    """

    """
    Attempt to chunk the upload into acceptable size chunks, per BigQuery requirements
    """
    def chunked_upload(self, table_id, data):
        from google.cloud import bigquery
        client = bigquery.Client()
        error = None
        approx_max_request = 1000000.0  # 1MB

        data_len = len(data)
        approx_request_size = sys.getsizeof(json.dumps(data))
        approx_num_batches = math.ceil(approx_request_size / approx_max_request)
        rows_per_batch = math.floor(data_len / approx_num_batches)
        if rows_per_batch <= 1:
            rows_per_batch = 1

        tty.debug("Size: {}B".format(sys.getsizeof(json.dumps(data))))
        tty.debug("Length in rows: {}".format(data_len))
        tty.debug("Num Batches: {}".format(approx_num_batches))
        tty.debug("Rows per Batch: {}".format(rows_per_batch))

        for i in range(0, data_len, rows_per_batch):
            end = i + rows_per_batch
            if end > data_len:
                end = data_len
            tty.debug("Uploading rows {} to {}".format(i, end))
            error = client.insert_rows_json(table_id, data[i:end])
            if error:
                return error
        return error

    def insert_data(self, uri: str, workspace_name, results) -> None:

        # It is expected that the user will create these tables outside of this
        # tooling
        exp_table_id = "{uri}.{table_name}".format(uri=uri, table_name="experiments")
        fom_table_id = "{uri}.{table_name}".format(uri=uri, table_name="foms")

        exps_to_insert = []
        foms_to_insert = []

        for experiment in results:
            exps_to_insert.append(experiment.to_json())

            for fom in experiment.foms:
                fom_data = fom
                fom_data['experiment_id'] = experiment.get_hash()
                fom_data['experiment_name'] = experiment.name
                foms_to_insert.append(fom_data)

        tty.debug("Experiments to insert:")
        tty.debug(exps_to_insert)

        tty.msg("Upload experiments...")
        errors1 = self.chunked_upload(exp_table_id, exps_to_insert)
        errors2 = None

        if errors1 == []:
            tty.msg("Upload FOMs...")
            errors2 = self.chunked_upload(fom_table_id, foms_to_insert)

        for errors, name in zip([errors1, errors2], ['exp', 'fom']):
            if errors == []:
                tty.msg("New rows have been added in {}.".format(name))
            else:
                tty.die("Encountered errors while inserting rows: {}".format(errors))

    def perform_upload(self, uri, workspace_name, results):
        super().perform_upload(uri, workspace_name, results)

        # import spack.util.spack_json as sjson
        # json_str = sjson.dump(results)

        self.insert_data(uri, workspace_name, results)

    # def get_max_current_id(uri, table):
        # TODO: Generating an id based on the max in use id is dangerous, and
        # technically gives a race condition in parallel, and should be done in
        # a more graceful and scalable way..  like hashing the experiment? or
        # generating a known unique id for it
        # query = "SELECT MAX(id) FROM `{uri}.{table}` LIMIT 1".format(uri=uri, table=table)
        # query_job = client.query(query)
        # results = query_job.result()  # Waits for job to complete.
        # return results[0]

    def get_expierment_id(experiment):
        # get_max_current_id(...) # Warning: dangerous..

        # This should be stable per machine/python version, but is not
        # guaranteed to be globally stable
        return hash(json.dumps(experiment, sort_keys=True))
