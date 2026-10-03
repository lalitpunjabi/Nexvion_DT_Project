variable "aws_region" {
  description = "AWS Region for Nexvion infrastructure"
  type        = string
  default     = "ap-south-1"
}

variable "environment" {
  description = "Deployment environment scope"
  type        = string
  default     = "staging"
}

variable "vpc_cidr" {
  description = "CIDR block for the existing Nexvion VPC"
  type        = string
  default     = "172.31.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block for the existing Nexvion subnet"
  type        = string
  default     = "172.31.0.0/20"
}

variable "availability_zone" {
  description = "AWS Availability Zone"
  type        = string
  default     = "ap-south-1b"
}

variable "instance_type" {
  description = "EC2 Instance type"
  type        = string
  default     = "t3.small"
}

variable "ami_id" {
  description = "AMI ID of the existing EC2 instance"
  type        = string
  default     = "ami-01a00762f46d584a1"
}

variable "key_name" {
  description = "AWS EC2 SSH Key Pair name"
  type        = string
  default     = "Nexvion"
}

variable "root_volume_size" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 20
}

# ------------------------------------------------------------------------------
# EKS Cluster & Node Group Variables (Phase 4.4)
# ------------------------------------------------------------------------------
variable "eks_cluster_name" {
  description = "Name of the Amazon EKS cluster"
  type        = string
  default     = "nexvion-eks"
}

variable "eks_cluster_version" {
  description = "Kubernetes control plane version for EKS (1.36 Standard Support)"
  type        = string
  default     = "1.36"
}

variable "eks_subnet_cidr_a" {
  description = "CIDR block for the additional EKS public subnet in ap-south-1a"
  type        = string
  default     = "172.31.16.0/20"
}

variable "eks_az_a" {
  description = "Availability Zone for the additional EKS subnet"
  type        = string
  default     = "ap-south-1a"
}

variable "eks_node_group_name" {
  description = "Name of the EKS managed node group"
  type        = string
  default     = "nexvion-node-group"
}

variable "eks_node_instance_types" {
  description = "EC2 Instance types for EKS managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "eks_desired_capacity" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 2
}

variable "eks_min_capacity" {
  description = "Minimum number of worker nodes"
  type        = number
  default     = 1
}

variable "eks_max_capacity" {
  description = "Maximum number of worker nodes"
  type        = number
  default     = 3
}

