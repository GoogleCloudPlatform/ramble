taskGroups:
  - taskSpec:
      runnables:
        - script:
            text: |
{batch_formatted_command}
    task_count: {n_nodes}
    task_count_per_node: 1
    require_hosts_file: true
    permissive_ssh: true
allocation_policy:
  instances:
    - policy:
        machine_type: {batch_machine_type}
        boot_disk:
          image: {batch_machine_image}
          size_gb: {batch_disk_size}
  location:
    allowed_locations:
      - regions/{batch_job_region}
      - zones/{batch_job_zone}
logs_policy:
  destination: CLOUD_LOGGING
