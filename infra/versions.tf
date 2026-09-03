terraform {
  required_version = ">= 1.5"

  backend "s3" {} # partial config; bucket/key/region/dynamodb_table provided via -backend-config

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}
