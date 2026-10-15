#!/bin/bash
echo "========================"
echo "Print out mpi job status"
echo "========================"
echo ""
kubectl describe mpijobs {job_name}

lname=$(kubectl get pods | grep '{job_name}-launcher' | awk '{print $1}')
if [ ! -z "$lname" ]; then
    echo " "
    echo "=========================="
    echo "Print out the launcher log"
    echo "=========================="
    echo " "
    kubectl logs $lname | tee {experiment_run_dir}/launcher.log
fi
