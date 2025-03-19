# Configure the AWS provider with the region specified in variables
provider "aws" {
    region = var.aws_region
}

# Create an EKS (Elastic Kubernetes Service) cluster using a public module
module "eks" {
    source  = "terraform-aws-modules/eks/aws"
    version = "~> 19.0"

    # Set basic cluster properties
    cluster_name    = var.cluster_name
    cluster_version = "1.28"

    # VPC and subnet configuration for the cluster
    vpc_id     = module.vpc.vpc_id
    subnet_ids = module.vpc.private_subnets

    # Set default configuration for managed node groups for the cluster
    eks_managed_node_group_defaults = {
        ami_type       = "AL2_x86_64"
        instance_types = ["t3.medium"]    
        attach_cluster_primary_security_group = true
    }

    # Define the default managed node group with autoscaling settings
    eks_managed_node_groups = {
        default_node_group = {
            min_size     = 2
            max_size     = 3
            desired_size = 2
            instance_types = ["t3.medium"]
            capacity_type  = "ON_DEMAND"
        }
    }

    # Add an egress rule to allow the cluster nodes to communicate with ECR (pull images etc.)
    node_security_group_additional_rules = {
        egress_all = {
            description      = "Allow all egress"
            protocol         = "-1"
            from_port        = 0
            to_port          = 0
            type             = "egress"
            cidr_blocks      = ["0.0.0.0/0"]
            ipv6_cidr_blocks = ["::/0"]
        }
    }

    # Tag the EKS cluster for organization and management
    tags = {
        Environment = "dev"
        Project     = "weather-service"
    }
}

# Create a VPC (Virtual Private Cloud) for the EKS cluster using a public module
module "vpc" {
    source  = "terraform-aws-modules/vpc/aws"
    version = "~> 5.0"

    # Set VPC name and IP address range
    name = "${var.cluster_name}-vpc"
    cidr = "10.0.0.0/16"

    # Define the availability zones and both private and public subnet CIDRs
    azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
    private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
    public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

    # Enable NAT gateway and DNS hostnames for private subnets
    enable_nat_gateway   = true
    single_nat_gateway   = true
    enable_dns_hostnames = true

    # General tags for the VPC resources
    tags = {
        "kubernetes.io/cluster/${var.cluster_name}" = "shared"
        Environment = "dev"
        Project     = "weather-service"
    }

    # Tags specific to public subnets for load balancers
    public_subnet_tags = {
        "kubernetes.io/cluster/${var.cluster_name}" = "shared"
        "kubernetes.io/role/elb"                    = "1"
    }

    # Tags specific to private subnets for internal load balancers
    private_subnet_tags = {
        "kubernetes.io/cluster/${var.cluster_name}" = "shared"
        "kubernetes.io/role/internal-elb"           = "1"
    }
}

# Output the command to update the kubeconfig to connect to the EKS cluster
output "kubeconfig_command" {
    description = "Command to update kubeconfig"
    value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${var.cluster_name}"
}