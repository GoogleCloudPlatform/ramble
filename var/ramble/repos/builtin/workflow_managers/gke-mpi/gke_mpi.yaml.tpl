apiVersion: kubeflow.org/v2beta1
kind: MPIJob
metadata:
  name: {job_name}
{extra_metadata_section}
spec:
  slotsPerWorker: {cores_per_node}
  runPolicy:
    cleanPodPolicy: Running
  mpiReplicaSpecs:
    Launcher:
      replicas: 1
      template:
        spec:
          hostPID: true
          hostIPC: true
          dnsPolicy: ClusterFirstWithHostNet
          volumes:
          - name: config
            configMap:
              name: gke-mpi-config
          containers:
          - image: {container_image}
            name: mpi-launcher
            volumeMounts:
            - name: config
              mountPath: /config
            command: ["bash", "{launcher_script_path}"]
            securityContext:
              privileged: true
    Worker:
      replicas: {n_nodes}
      template:
        spec:
          containers:
          - image: {container_image}
            name: mpi-worker
            securityContext:
              privileged: true
            volumeMounts:
            - name: config
              mountPath: /config
            command: ["bash", "{worker_script_path}"]
          volumes:
          - name: config
            configMap:
              name: gke-mpi-config
            