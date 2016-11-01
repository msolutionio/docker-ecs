#!/usr/bin/env python3
__author__ = 'Victor Schubert'
__version__ = '0.1'

import argparse
import json
import subprocess
import tempfile

import boto3


ecs = boto3.client('ecs')
elbv2 = boto3.client('elbv2')
ec2 = boto3.client('ec2')


CONFIG = {
    'ecsInstanceProfile': 'arn:aws:iam::',
    'ecsServiceRole': 'arn:aws:iam::',
    'ecs_ami': 'ami-xxxxxxxx',
    'elb_security_group': 'sg-xxxxxxxx',
    'instance_type': 't2.micro',
    'instance_amount_per_subnet': 2,
    'keypair_name': 'xxxx',
    'vpc_id': 'vpc-xxxxxxxx',
    'vpc_subnets': ['subnet-xxxxxxxx', 'subnet-xxxxxxxx'],
}


def ecs_from_dc(dc_path):
    """Reads a docker-compose file to return an ECS task definition.
    
    Positional arguments:
    dc_path -- Path to the docker-compose file.
    """
    with open(dc_path, 'r') as dc_file, tempfile.TemporaryFile('w+t') as tmp:
        subprocess.check_call(
            [
                '/usr/bin/env',
                'docker',
                'run',
                '--rm',
                '-i',
                'micahhausler/container-transform'
            ],
            stdin=dc_file,
            stdout=tmp,
        )
        tmp.seek(0)
        ecs_task_definition = json.load(tmp)
        return ecs_task_definition


def register_ecs(family, task_role_arn, ecs_task_definition):
    """Register an ECS task definition and return it.
    
    Positional parameters:
                 family -- the name of the task family
          task_role_arn -- the ARN of the task's role
    ecs_task_definition -- the task definition, as returned by Micah
                           Hausler's script
    """
    ecs_task_definition['family'] = family
    ecs_task_definition['taskRoleArn'] = task_role_arn
    return ecs.register_task_definition(
        **ecs_task_definition
    )


def create_load_balancer(name, subnets, security_groups):
    """Create an Elastic Load Balancer and return it.
    
    Positional parameters:
               name -- Name of the load balancer
            subnets -- Subnetworks for the load balancer
    security_groups -- Security groups for the load balancer
    """
    return elbv2.create_load_balancer(
        Name=name,
        Subnets=subnets,
        SecurityGroups=security_groups,
    )


def create_cluster(name):
    """Create an ECS cluster, return it.
    
    Positional parameters:
    name -- Name for the cluster, must be unique.
    """
    return ecs.create_cluster(
        clusterName=name, # Case consistency much?
    )


def create_instances(
  ami_id,
  subnet,
  security_groups,
  amount,
  instance_type,
  cluster_name,
  profile_arn,
):
    """Create ECS container instances and return them.
    
    Positional parameters:
             ami_id -- ID of the AMI for the instances
             subnet -- Subnet for the instances
    security_groups -- Security groups for the instances
             amount -- Amount of instances to run
      instance_type -- Type of the instances
       cluster_name -- Name of the cluster to participate in
        profile_arn -- ARN of the `ecsInstanceProfile' profile
    """
    return ec2.run_instances(
        ImageId=ami_id,
        SecurityGroupIds=security_groups,
        SubnetId=subnet,
        IamInstanceProfile={
            'Arn': profile_arn,
        },
        MinCount=amount,
        MaxCount=amount,
        InstanceType=instance_type,
        UserData="""#!/bin/bash
          echo ECS_CLUSTER={} >> /etc/ecs/ecs.config
        """.format(cluster_name),
    )


def create_balanced_service(
  cluster_name,
  family,
  load_balancer_name,
  load_balancer_arn,
  protocol,
  port,
  container_name,
  vpc_id,
  ecs_service_role,
  service_name,
  task_amount,
):
    """Create a service and return it.
    
    Positional parameters:
          cluster_name -- Name of the cluster
                family -- Family of the task definition
    load_balancer_name -- Name of the load balancer
     load_balancer_arn -- ARN of the load balancer
              protocol -- Protocol of the exposed port
                  port -- Number of the exposed port
        container_name -- Name of the container the port belongs to
                vpc_id -- ID of the current VPC
      ecs_service_role -- ARN of the `ecsServiceRole' role
          service_name -- Name of the service
           task_amount -- Desired amount of tasks
    """
    target_group = elbv2.create_target_group(
        Protocol=protocol,
        Port=port,
        VpcId=vpc_id,
        Name='{}-{}'.format(cluster_name, family),
    )
    target_group_arn = target_group['TargetGroups'][0]['TargetGroupArn']
    elbv2.create_listener(
        LoadBalancerArn=load_balancer_arn,
        Protocol=protocol,
        Port=port,
        DefaultActions=[
            {
                'Type': 'forward',
                'TargetGroupArn': target_group_arn,
            }
        ],
    )
    return ecs.create_service(
        cluster=cluster_name,
        serviceName=service_name,
        taskDefinition=family,
        role=ecs_service_role,
        loadBalancers=[
            {
                'targetGroupArn': target_group_arn,
                'containerName': container_name,
                'containerPort': port,
            }
        ],
        desiredCount=task_amount,
    )


def main(
  dc_path,
  family,
  task_role_arn,
  load_balancer_name,
  cluster_name,
  protocol,
  port,
  container_name,
  service_name,
  task_count,
):
    ecs_task_definition = ecs_from_dc(dc_path)
    print('File converted.')
    register_ecs(family, task_role_arn, ecs_task_definition)
    print('Task definition registered.')
    load_balancer = create_load_balancer(
        load_balancer_name,
        CONFIG['vpc_subnets'],
        [CONFIG['elb_security_group']],
    )
    load_balancer_arn = load_balancer['LoadBalancers'][0]['LoadBalancerArn']
    print('Load balancer created.')
    create_cluster(
        cluster_name,
    )
    print('Cluster created.')
    for subnet in CONFIG['vpc_subnets']:
        create_instances(
            CONFIG['ecs_ami'],
            subnet,
            [CONFIG['elb_security_group']],
            CONFIG['instance_amount_per_subnet'],
            CONFIG['instance_type'],
            cluster_name,
            CONFIG['ecsInstanceProfile'],
        )
    print('Instances started.')
    create_balanced_service(
        cluster_name,
        family,
        load_balancer_name,
        load_balancer_arn,
        protocol,
        port,
        container_name,
        CONFIG['vpc_id'],
        CONFIG['ecsServiceRole'],
        service_name,
        task_count,
    )
    print('Service started.')



if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Setup clustered, load balanced ECS tasks.',
    )
    parser.add_argument('--task-count',
        dest='task_count',
        type=int,
        default=1,
        help=("Number of tasks to be run on the cluster. Will be balanced "
              "between all container instances."),
    )
    parser.add_argument('--task-role-arn',
        dest='task_role_arn',
        type=str,
        default='',
        help=("ARN of the IAM role the task will endorse."),
    )
    parser.add_argument('--task-family-name',
        dest='family_name',
        type=str,
        default='my-family',
        help=("Name of the service family. Services are versionned, and "
              "versions of the same service must have the same family name."),
    )
    parser.add_argument('--load-balancer-name',
        dest='load_balancer_name',
        type=str,
        default='my-lb',
        help=("Name of the load balancer which will be created."),
    )
    parser.add_argument('--cluster-name',
        dest='cluster_name',
        type=str,
        default='my-cluster',
        help=("Name of the cluster which will be created."),
    )
    parser.add_argument('--service-protocol',
        dest='protocol',
        type=str,
        choices=['HTTP', 'TCP', 'UDP'],
        required=True,
        help=("Protocol used by the exposed port."),
    )
    parser.add_argument('--service-port',
        dest='port',
        type=int,
        required=True,
        help=("Number of the exposed port."),
    )
    parser.add_argument('--service-container',
        dest='container_name',
        type=str,
        required=True,
        help=("Name of the container the port belongs to. This is the same as "
              "the key under which the container is described in the "
              "docker-compose file."),
    )
    parser.add_argument('--service-name',
        dest='service_name',
        type=str,
        default='my-service',
        help=("Name of the ECS service which will be created."),
    )
    parser.add_argument('dc_path',
        type=str,
        help=("Path to the docker-compose file to be deployed."),
    )
    args = parser.parse_args()
    main(
        args.dc_path,
        args.family_name,
        args.task_role_arn,
        args.load_balancer_name,
        args.cluster_name,
        args.protocol,
        args.port,
        args.container_name,
        args.service_name,
        args.task_count,
    )
