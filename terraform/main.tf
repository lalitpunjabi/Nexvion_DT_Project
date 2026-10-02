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
