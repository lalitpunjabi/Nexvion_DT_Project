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
