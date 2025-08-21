terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
  
  backend "s3" {
    # Backend configuration will be provided via backend-config file
    # bucket         = "knowledge-db-terraform-state"
    # key            = "infrastructure/terraform.tfstate"
    # region         = "us-west-2"
    # encrypt        = true
    # dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "knowledge-database"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = var.project_owner
      CostCenter  = var.cost_center
    }
  }
}

provider "random" {}