variable "location" {
    description = "The Azure Region in which all resources will be created."
    default     = "eastus"
}

variable "name" {
    type        = string
    description = "The name of the application."
    default     = "restowo"
}

variable "sql_db_name" {
    type        = string
    description = "The name of the SQL database."
    default     = "restowo-db"
}

variable "environment" {
    description = "The environment in which the application will be deployed."
    default     = "dev001"
}

variable "python_version" {
    description = "The Python version for the App Service"
    default     = "3.9.0"
}

variable "admin_username" {
  type        = string
  description = "The administrator username of the SQL logical server."
  default     = "gerou"
}

variable "admin_password" {
  type        = string
  description = "The administrator password of the SQL logical server."
  sensitive   = true
  default     = null
}
