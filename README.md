# Deploying docker-compose files on AWS ECS

This is an example usage of the concepts presented in our article [_Deploying
docker-compose files on AWS
ECS_](https://www.msolution.io/2016/11/01/deploying-docker-compose-files-on-aws-ecs/)
which shows how to deploy docker-compose services directly on _AWS ECS_ using
_Boto 3_.

# Usage

This example can deploy a docker-compose file on AWS, by creating a load
balancer and an ECS cluster with a few instances. Otherwise it is fairly
limited in that it cannot handle services with more than one exposed port on
one service.

This script __will not__ work out-of-the-box. You must first set the values of
the `CONFIG` global variable at line 18.

## `CONFIG` values

### `ecsInstanceProfile`

ARN of the `ecsInstanceProfile` profile created following the instructions of
the article.

### `ecsServiceRole`

ARN of the `ecsServicRole` role created following the instructions of the
article.

### `ecs_ami`

AMI of Amazon's ECS-optimized AMI for your region.

### `elb_security_group`

Security group for the created load balancer.

### `instance_type`

Type of the created instances.

### `instance_amount_per_subnet`

Amount of instances which will be created on each subnetwork.

### `keypair_name`

Keypair to be used when creating the instances for the ECS cluster.

### `vpc_id`

ID of the VPC in which everything will be created.

### `vpc_subnets`

List of subnetworks in which instances will be run. There must be at least two.
No two subnets must be in the same _Availability Zone_.

## Command line options

```
usage: deploy.py [-h] [--task-count TASK_COUNT]
                 [--task-role-arn TASK_ROLE_ARN]
                 [--task-family-name FAMILY_NAME]
                 [--load-balancer-name LOAD_BALANCER_NAME]
                 [--cluster-name CLUSTER_NAME] --service-protocol
                 {HTTP,TCP,UDP} --service-port PORT --service-container
                 CONTAINER_NAME [--service-name SERVICE_NAME]
                 dc_path

Setup clustered, load balanced ECS tasks.

positional arguments:
  dc_path               Path to the docker-compose file to be deployed.

optional arguments:
  -h, --help            show this help message and exit
  --task-count TASK_COUNT
                        Number of tasks to be run on the cluster. Will be
                        balanced between all container instances.
  --task-role-arn TASK_ROLE_ARN
                        ARN of the IAM role the task will endorse.
  --task-family-name FAMILY_NAME
                        Name of the service family. Services are versionned,
                        and versions of the same service must have the same
                        family name.
  --load-balancer-name LOAD_BALANCER_NAME
                        Name of the load balancer which will be created.
  --cluster-name CLUSTER_NAME
                        Name of the cluster which will be created.
  --service-protocol {HTTP,TCP,UDP}
                        Protocol used by the exposed port.
  --service-port PORT   Number of the exposed port.
  --service-container CONTAINER_NAME
                        Name of the container the port belongs to. This is the
                        same as the key under which the container is described
                        in the docker-compose file.
  --service-name SERVICE_NAME
                        Name of the ECS service which will be created.
```
