# ------------------------------------------------------------------------------
# 1. Existing AWS VPC & Networking Infrastructure
# ------------------------------------------------------------------------------
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {}
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = {}
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.subnet_cidr
  map_public_ip_on_launch = true
  availability_zone       = var.availability_zone

  tags = {}
}

resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {}
}

# ------------------------------------------------------------------------------
# 2. Existing Security Group (launch-wizard-9 / sg-0e2c619a238e449df)
# ------------------------------------------------------------------------------
resource "aws_security_group" "ec2_sg" {
  name        = "launch-wizard-9"
  description = "launch-wizard-9 created 2026-10-02T09:13:18.654Z"
  vpc_id      = aws_vpc.main.id

  ingress {
    description      = ""
    from_port        = 22
    to_port          = 22
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
  }

  ingress {
    description      = ""
    from_port        = 80
    to_port          = 80
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
  }

  ingress {
    description      = ""
    from_port        = 443
    to_port          = 443
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
  }

  ingress {
    description      = ""
    from_port        = 8080
    to_port          = 8080
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
  }

  ingress {
    description      = ""
    from_port        = 8081
    to_port          = 8081
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
  }

  egress {
    description      = ""
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = []
    prefix_list_ids  = []
    security_groups  = []
    self             = false
  }

  tags = {}
}

# ------------------------------------------------------------------------------
# 3. Existing EC2 Compute Instance (i-057f6d6d0bbb33b37)
# ------------------------------------------------------------------------------
resource "aws_instance" "nexvion_server" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  key_name               = var.key_name
  availability_zone      = var.availability_zone

  root_block_device {
    volume_size           = var.root_volume_size
    volume_type           = "gp3"
    encrypted             = false
    delete_on_termination = true
  }

  tags = {
    Name = "Nexvion"
  }

  lifecycle {
    ignore_changes = [
      user_data,
      user_data_base64
    ]
  }
}

# ------------------------------------------------------------------------------
# 4. Existing Elastic IP & Association (eipalloc-0662e014367e516bf)
# ------------------------------------------------------------------------------
resource "aws_eip" "nexvion_eip" {
  domain = "vpc"
  tags = {
    Name = "Nexvion"
  }
}

resource "aws_eip_association" "nexvion_eip_assoc" {
  allocation_id = aws_eip.nexvion_eip.id
  instance_id   = aws_instance.nexvion_server.id
}

# ------------------------------------------------------------------------------
# 5. Terraform Import Blocks for Existing AWS Infrastructure
# ------------------------------------------------------------------------------
import {
  to = aws_vpc.main
  id = "vpc-09df3f5fdabdcf81f"
}

import {
  to = aws_subnet.public
  id = "subnet-048f480df580a47f8"
}

import {
  to = aws_internet_gateway.gw
  id = "igw-045a89bde29483b3a"
}

import {
  to = aws_route_table.main
  id = "rtb-0b5c00adb98133d97"
}

import {
  to = aws_security_group.ec2_sg
  id = "sg-0e2c619a238e449df"
}

import {
  to = aws_instance.nexvion_server
  id = "i-057f6d6d0bbb33b37"
}

import {
  to = aws_eip.nexvion_eip
  id = "eipalloc-0662e014367e516bf"
}

import {
  to = aws_eip_association.nexvion_eip_assoc
  id = "eipassoc-0dfe320300f89e0da"
}

# ------------------------------------------------------------------------------
# 6. Amazon ECR Container Registry Infrastructure (Phase 4.3)
# ------------------------------------------------------------------------------
resource "aws_ecr_repository" "nexvion" {
  name                 = "nexvion-web"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "nexvion" {
  repository = aws_ecr_repository.nexvion.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Expire untagged images older than 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Retain maximum 30 tagged Git SHA images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 30
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ------------------------------------------------------------------------------
# 7. Amazon EKS Cluster & Node Group Infrastructure (Phase 4.4)
# ------------------------------------------------------------------------------

# Additional Public Subnet in ap-south-1a for EKS multi-AZ requirement
resource "aws_subnet" "eks_public_a" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = var.eks_subnet_cidr_a
  map_public_ip_on_launch = true
  availability_zone       = var.eks_az_a

  tags = {
    Name                                            = "nexvion-eks-public-a"
    "kubernetes.io/cluster/${var.eks_cluster_name}" = "shared"
    "kubernetes.io/role/elb"                        = "1"
  }
}

resource "aws_route_table_association" "eks_public_a_assoc" {
  subnet_id      = aws_subnet.eks_public_a.id
  route_table_id = aws_route_table.main.id
}

# --- EKS Cluster IAM Role & Policy Attachments ---
resource "aws_iam_role" "eks_cluster" {
  name = "nexvion-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

# --- EKS Control Plane Cluster Resource ---
resource "aws_eks_cluster" "nexvion" {
  name     = var.eks_cluster_name
  role_arn = aws_iam_role.eks_cluster.arn
  version  = var.eks_cluster_version

  vpc_config {
    subnet_ids              = [aws_subnet.public.id, aws_subnet.eks_public_a.id]
    endpoint_public_access  = true
    endpoint_private_access = true
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy
  ]
}

resource "aws_security_group_rule" "eks_cluster_ingress_vpc" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  security_group_id = aws_eks_cluster.nexvion.vpc_config[0].cluster_security_group_id
  cidr_blocks       = ["172.31.0.0/16"]
  description       = "Allow VPC instances (Jenkins EC2) to communicate with EKS control plane API"
}


# --- EKS Worker Node Group IAM Role & Policy Attachments ---
resource "aws_iam_role" "eks_node_group" {
  name = "nexvion-eks-node-group-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node_group.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node_group.name
}

resource "aws_iam_role_policy_attachment" "eks_ecr_read_only" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node_group.name
}

# --- EKS Managed Node Group Resource ---
resource "aws_eks_node_group" "nexvion" {
  cluster_name    = aws_eks_cluster.nexvion.name
  node_group_name = var.eks_node_group_name
  node_role_arn   = aws_iam_role.eks_node_group.arn
  subnet_ids      = [aws_subnet.public.id, aws_subnet.eks_public_a.id]

  instance_types = var.eks_node_instance_types
  capacity_type  = "ON_DEMAND"

  scaling_config {
    desired_size = var.eks_desired_capacity
    max_size     = var.eks_max_capacity
    min_size     = var.eks_min_capacity
  }

  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_worker_node_policy,
    aws_iam_role_policy_attachment.eks_cni_policy,
    aws_iam_role_policy_attachment.eks_ecr_read_only
  ]
}

# --- EKS Core Add-ons ---
resource "aws_eks_addon" "vpc_cni" {
  cluster_name = aws_eks_cluster.nexvion.name
  addon_name   = "vpc-cni"
}

resource "aws_eks_addon" "coredns" {
  cluster_name = aws_eks_cluster.nexvion.name
  addon_name   = "coredns"
  depends_on   = [aws_eks_node_group.nexvion]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name = aws_eks_cluster.nexvion.name
  addon_name   = "kube-proxy"
}



