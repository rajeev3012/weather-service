variable "aws_region" {
  description = "AWS region to deploy the EKS cluster"
  type        = string
  default     = "eu-west-1"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "weather-service-cluster"
}