# We strongly recommend using the required_providers block to set the
# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.91.0"
    }
    databricks = {
      source = "databricks/databricks"
    }
  } 
}

# Configure the Microsoft Azure Provider
provider "azurerm" {
  features {}

  client_id     = "104ecaec-745f-48e4-9b9b-990ea236f08c"
  client_secret = "F4a8Q~lm2OMLLmCUyFim8Mlcc~E6egW6Pn500aol"
  tenant_id     = "fb12b490-1ec9-403e-a67b-c94c3d50ea31"
  subscription_id = "dae8e77f-f000-4c37-8da1-6817590cceff"
}

data "azurerm_resource_group" "dev_rg" {
  name = "tyler-dataengineer-dev-canadaeast"
}

provider "databricks" {
  host  = "https://adb-213311967472827.7.azuredatabricks.net"
  token = "dapif1e5eff8b1845709f84ed50735953503-3"
}

data "databricks_cluster" "existing_cluster" {
  cluster_id = "1023-200934-b5lifk79"
}


#data "local_file" "notebook" {
#  filename = "/Users/yuehuang/Downloads/Terraform_Azure1/my_notebook.py"
#}

resource "databricks_workspace_file" "weather_data_ingestion_function_unit_test" {
  source = "./src/weather/weather_data_ingestion_function_unit_test.py"
  path   = "/Workspace/Users/huangyue1752@gmail.com/test/weather_data_ingestion_function_unit_test.py"

}

resource "databricks_workspace_file" "weather_data_ingestion_function" {
  source = "./src/weather/weather_data_ingestion_function.py"
  path   = "/Workspace/Users/huangyue1752@gmail.com/test/weather_data_ingestion_function.py"

}

resource "databricks_workspace_file" "scd_type_two_function_unit_test" {
  source = "./src/scd_type_two_function_unit_test.py"
  path   = "/Workspace/Users/huangyue1752@gmail.com/test/scd_type_two_function_unit_test.py"

}

resource "databricks_workspace_file" "scd_type_two_function" {
  source = "./src/scd_type_two_function.py"
  path   = "/Workspace/Users/huangyue1752@gmail.com/test/scd_type_two_function.py"

}

resource "databricks_workspace_file" "data_process_function_unit_test" {
  source = "./src/data_process_function_unit_test.py"
  path   = "/Workspace/Users/huangyue1752@gmail.com/test/data_process_function_unit_test.py"

}

resource "databricks_notebook" "data_process_function" {
  source = "./src/data_process_function.ipynb"
  path   = "/Workspace/Users/huangyue1752@gmail.com/test/data_process_function.ipynb"

}



resource "databricks_job" "job_dev_" {
  name = "Terraform_ETL_stream_${var.environment}"

  # Reference the existing cluster by its cluster ID
    task {
    task_key = "scd_type2_test"
    description = "Run scd_type2_test"
    existing_cluster_id = data.databricks_cluster.existing_cluster.cluster_id
    spark_python_task {
      python_file = "/Workspace/Users/huangyue1752@gmail.com/test/scd_type_two_function_unit_test.py"
    }
  }
    task {
    task_key = "scd_type2"
    description = "Run scd_type2"
    existing_cluster_id = data.databricks_cluster.existing_cluster.cluster_id
    spark_python_task {
      python_file = "/Workspace/Users/huangyue1752@gmail.com/test/scd_type_two_function.py"
    }

    # Set the dependency on the first task (unit test)
     depends_on {
           task_key =   "scd_type2_test"
   }   
  }

  # Define the first task that runs the unit test Python script
  task {
    task_key = "task_unit_test"
    description = "Run weather data ingestion unit test"
    existing_cluster_id = data.databricks_cluster.existing_cluster.cluster_id
    spark_python_task {
      python_file = "/Workspace/Users/huangyue1752@gmail.com/test/weather_data_ingestion_function_unit_test.py"
    }
     depends_on {
           task_key =   "scd_type2"
   } 
  }

  # Define the second task that runs the data ingestion Python script
  task {
    task_key = "task_ingestion"
    description = "Run weather data ingestion"
    existing_cluster_id = data.databricks_cluster.existing_cluster.cluster_id
    spark_python_task {
      python_file = "/Workspace/Users/huangyue1752@gmail.com/test/weather_data_ingestion_function.py"
    }

    # Set the dependency on the first task (unit test)
     depends_on {
           task_key =   "task_unit_test"
   }   
  }

  task {
    task_key = "data_process_function_unit_test"
    description = "Run data_process_function_unit_test"
    existing_cluster_id = data.databricks_cluster.existing_cluster.cluster_id
    spark_python_task {
      python_file = "/Workspace/Users/huangyue1752@gmail.com/test/data_process_function_unit_test.py"
    }
     depends_on {
           task_key =   "scd_type2"
   } 
  }

  task {
    task_key = "data_process_function"
    description = "Run data_process_function"
    existing_cluster_id = data.databricks_cluster.existing_cluster.cluster_id
    notebook_task {
      notebook_path = "/Workspace/Users/huangyue1752@gmail.com/test/data_process_function.ipynb"
    }
     depends_on {
           task_key =   "data_process_function_unit_test"
   } 
  }

}

# Use null_resource with local-exec to trigger the job run using the Databricks REST API
resource "null_resource" "trigger_job_run" {
  depends_on = [databricks_job.job_dev_]  # Ensure the job is created first

  triggers = {
    job_id = "${databricks_job.job_dev_.id}"  # Re-run if job ID changes
    # You can also add other dynamic conditions here if needed
  }
  provisioner "local-exec" {
    command = <<EOT
      curl -X POST https://adb-213311967472827.7.azuredatabricks.net/api/2.1/jobs/run-now \
      -H "Authorization: Bearer ${var.databricks_token}" \
      -d '{"job_id": "${databricks_job.job_dev_.id}"}'
    EOT
  }
}
