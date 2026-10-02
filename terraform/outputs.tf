output "vpc_id" {
  description = "The ID of the existing Nexvion VPC"
  value       = aws_vpc.main.id
}

output "subnet_id" {
  description = "The ID of the existing Nexvion Subnet"
  value       = aws_subnet.public.id
}

output "security_group_id" {
  description = "The Security Group ID associated with the EC2 instance"
  value       = aws_security_group.ec2_sg.id
}

output "instance_id" {
  description = "The EC2 Instance ID of the Nexvion DevOps server"
  value       = aws_instance.nexvion_server.id
}

output "elastic_ip" {
  description = "Elastic IP address allocated to the Nexvion DevOps server"
  value       = aws_eip.nexvion_eip.public_ip
}

output "instance_public_ip" {
  description = "Public IP address of the Nexvion DevOps server (Elastic IP: 52.66.25.69)"
  value       = aws_eip.nexvion_eip.public_ip
}

output "jenkins_url" {
  description = "URL for accessing Jenkins CI/CD Controller GUI"
  value       = "http://${aws_eip.nexvion_eip.public_ip}:8080"
}

output "nexvion_staging_url" {
  description = "URL for accessing Nexvion Staging E-Commerce Web Application"
  value       = "http://${aws_eip.nexvion_eip.public_ip}:8081"
}

output "ecr_repository_url" {
  description = "The full repository URL of the Nexvion ECR container registry"
  value       = aws_ecr_repository.nexvion.repository_url
}

output "ecr_repository_name" {
  description = "The name of the Nexvion ECR container registry"
  value       = aws_ecr_repository.nexvion.name
}

