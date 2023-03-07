import llnl.util.tty as tty

class Uploader():
    # TODO: should the class store the base uri?
    def perform_upload(self, uri, workspace_name, data):
        # TODO: move content checking to __init__ ?
        if not uri:
            raise ValueError(
                "%s requires %s argument." % (self.__class__, uri))
        if not data:
            raise ValueError(
                "%s requires %s argument." % (self.__class__, json_str))
        pass

'''
Class representation of experiment data
'''
class Experiment():
    def __init__(self, name, data):
        self.name = name
        self.foms = []
        self.id = None # This is essentially the hash
        self.data = data
        self.application_name = data['RAMBLE_VARIABLES']['application_name']
        self.bulk_hash = None # proxy for workspace or "uploaded with"
        self.n_nodes = data['RAMBLE_VARIABLES']['n_nodes']
        self.processes_per_node = data['RAMBLE_VARIABLES']['processes_per_node']
        self.n_ranks = data['RAMBLE_VARIABLES']['n_ranks']
        self.n_threads = data['RAMBLE_VARIABLES']['n_threads']
        #'platform' # TODO: add this

        self.id = None # TODO: find a good way to set this once the object is "finished"

    def generate_hash(self):
        # Avoid regenerating a hash when possible
        # (The hash of an object must never change during its lifetime..)
        if self.id is None:
            # TODO: this might be better as a hash of something we intuatively
            # expect to be uniqie, like:
            # "{RAMBLE_STATUS}-{application_name}-{experiment_name}-{time}-etc"
            # If we don't want this, we can go back to this class just being a dict
            self.id = hash(self)
        return self.id

    def get_hash(self):
        return self.generate_hash()

    def to_json(self):
        import json
        #return json.dumps(self, default=lambda o: o.__dict__)
        #j = json.dumps( self.__dict__ )
        #print(type(j))

        # deep copy so the assignment below doesn't affect the foms array
        import copy
        j = copy.deepcopy(self.__dict__)

        j['foms'] = json.dumps(self.foms)
        j['data'] = json.dumps(self.data)
        return j



'''
Goal: convert results to a more searchable and decomposed format for insertion
into data store (etc)

Input:
    { expierment_name: { "CONTEXTS": { "context_name": "FOM_name { unit: "value", "value":value" }...}


Output: The general idea is the decompose the results into a more "database" like forwat, where the runs and FOMs are in a different table, giving:

experiments: {experiment_id, experiment details...}
foms: {experiment_id, fom_name, fom_value, fom_unit..} # +context?

results[table][row][data] ?
'''
@staticmethod
def format_data(data_in):
    tty.debug("Format Data in")
    tty.debug(data_in)
    results = []

    # TODO: what is the nice way to deal with the distinction between
    # numberic/float and string FOM values
    for exp in data_in['experiments']:
        if exp['RAMBLE_STATUS'] == 'SUCCESS':
            e = Experiment( exp['name'], exp )
            results.append( e )
            #experiment_id = exp.hash()
            #'experiment_id': experiment_id,
            for context in exp['CONTEXTS']:
                for fom in context['foms']:
                    e.foms.append(
                        {
                            'name': fom['name'],
                            'value' : fom['value'],
                            'unit': fom['units'],
                            'context': context['name'],
                        }
                    )

    return results



class BigQueryUploader(Uploader):
    from google.cloud import bigquery

    def insert_data(self, uri: str, workspace_name, results) -> None:

        # TODO: create these tables
        exp_table_id = "{uri}.{table_name}".format(uri=uri, table_name="experiments")
        fom_table_id = "{uri}.{table_name}".format(uri=uri, table_name="foms")

        client = bigquery.Client()

        exps_to_insert = []
        foms_to_insert = []

        from datetime import datetime
        current_dateTime = datetime.now()

        exps_hash = "{name}::{date}".format(name=workspace_name, date=current_dateTime)

        for experiment in results:
            experiment.generate_hash()
            experiment.bulk_hash = exps_hash

            exps_to_insert.append( experiment.to_json() )

            for fom in experiment.foms:
                fom_data = fom
                fom_data['experiment_id'] = experiment.get_hash()
                fom_data['experiment_name'] = experiment.name
                foms_to_insert.append( fom_data )

        tty.debug("Experiments to insert:")
        tty.debug(exps_to_insert)

        # Make an API request.
        errors1 = client.insert_rows_json(exp_table_id, exps_to_insert)
        errors2 = None
        if errors1 == []:
            errors2 = client.insert_rows_json(fom_table_id, foms_to_insert)

        for errors, name in zip([errors1, errors2], ['exp','fom']):
            if errors == []:
                tty.msg("New rows have been added in {}.".format(name))
            else:
                tty.die("Encountered errors while inserting rows: {}".format(errors))


    def perform_upload(self, uri, workspace_name, results):
        super().perform_upload(uri, workspace_name, results)

        # import spack.util.spack_json as sjson
        #json_str = sjson.dump(results)

        self.insert_data(uri, workspace_name, results)

    def get_max_current_id(uri, table):
        # TODO: Generating an id based on the max in use id is dangerous, and
        # technically gives a race condition in parallel, and should be done in
        # a more graceful and scalable way..  like hashing the experiment? or
        # generating a known unique id for it
        query = "SELECT MAX(id) FROM `{uri}.{table}` LIMIT 1".format(uri = uri, table = table)
        query_job = client.query(query)
        results = query_job.result()  # Waits for job to complete.
        return results[0]


    def get_expierment_id(experiment):
        #get_max_current_id(...) # Warning: dangerous..

        # This should be stable per machine/python version, but is not
        # guarnteed to be globally stable
        return hash(json.dumps(expiriment, sort_keys=True))

