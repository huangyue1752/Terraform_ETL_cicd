from pyspark.sql import SparkSession

def SCD2Function(catalog_name, db_name, table_name_stage, table_name_dim, catalog_source,db_name_source, table_name_source, column_names):
    # Start Spark session if not already started
    spark = SparkSession.builder.appName("SCD2 Function").getOrCreate()

    # Use the specified catalog and database
    spark.sql(f"use catalog {catalog_name}")
    spark.sql(f"use schema {db_name}")

    # Drop the staging table if it exists and create a new one
    spark.sql(f"DROP TABLE IF EXISTS {table_name_stage};")
    column_definitions = ", ".join([f"{col} STRING" for col in column_names])
    spark.sql(f"CREATE TABLE IF NOT EXISTS {table_name_stage} ({column_definitions}) USING DELTA;")

    # Truncate the staging table
    spark.sql(f"TRUNCATE TABLE {table_name_stage};")

    # Insert data into the staging table
    insert_query = f"INSERT INTO {table_name_stage} SELECT " + ", ".join([f"TRY_CAST({col} AS STRING)" for col in column_names]) + f" FROM {catalog_source}.{db_name_source}.{table_name_source};"
    spark.sql(insert_query)
    # Perform the merge for SCD Type 2
    merge_query = f"""
        MERGE INTO {table_name_dim} a
        USING (
            WITH q1 AS (
                SELECT * FROM {table_name_dim} WHERE {column_names[-1]} <> 'inactive'
            )
            SELECT {column_names[0]} AS mergeKey, * FROM {table_name_stage}
            UNION ALL
            SELECT NULL AS mergeKey, a.* 
            FROM {table_name_stage} a
            JOIN q1 b ON a.{column_names[0]} = b.{column_names[0]} 
            WHERE b.{column_names[-1]} <> 'inactive' AND (
                { ' OR '.join([f'a.{col} != b.{col}' for col in column_names[1:]]) }
            )
        ) b 
        ON a.{column_names[0]} = b.mergeKey and a.{column_names[-1]}='active'
        WHEN MATCHED AND (
            { ' OR '.join([f'b.{col} != a.{col}' for col in column_names[1:]]) }
        ) THEN 
            UPDATE SET 
                {column_names[-1]} = 'inactive',
                a.end_date = current_date() - 1 
        WHEN NOT MATCHED THEN 
            INSERT ({', '.join(column_names)}, start_date, end_date) 
            VALUES ({', '.join(column_names)}, current_date(), '9999-12-31');
    """
    
    spark.sql(merge_query)

# Example usage:
column_names = ["id", "body_html", "title", "handle", "product_type", "vendor", "created_at", "status"]
SCD2Function("streaming1", "silver", "stg_product", "dim_product", 
              "hive_metastore","_fivetran_setup_test", "product", column_names)
