variable "databricks_token" {
  description = "The Databricks API token"
  type        = string
}

variable "environment" {
  description = "The environment to deploy to (dev, qa, prod)"
  type        = string
}