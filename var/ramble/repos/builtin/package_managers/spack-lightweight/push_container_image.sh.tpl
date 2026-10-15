#!/bin/bash

{source_cmd}
{activate_cmd}

if ! spack mirror list | awk '{print $1}' | grep -q "{container_registry_name}"; then
  echo "Error: '{container_registry_name}' is not a valid Spack mirror." >&2
  echo "See https://spack.readthedocs.io/en/latest/containers.html#from-existing-installations on the mirror setup." >&2
  exit 1
fi

url=$(spack mirror list | grep "{container_registry_name}" | awk '{print $3)')
echo "Pushing container image to registry at $url"
spack buildcache push \
  --update-index \
  --base-image "{container_base_image}" \
  --tag "{container_image_tag}" {additional_args} \
  "{container_registry_name}"
