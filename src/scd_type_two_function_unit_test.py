import unittest
from unittest.mock import patch
from scd_type_two_function import SCD2Function  # Import the function to be tested

class TestSCD2Function(unittest.TestCase):

    @patch('pyspark.sql.SparkSession.sql')  # Mock the sql method
    def test_SCD2Function(self, mock_sql):
        # Test inputs
        catalog_name = "streaming1"
        db_name = "silver"
        table_name_stage = "stg_product"
        table_name_dim = "dim_product"
        catalog_source = "hive_metastore"
        db_name_source = "_fivetran_setup_test"
        table_name_source = "product"
        column_names = ["id", "body_html", "title", "handle", "product_type", "vendor", "created_at", "status"]

        # Call the function
        SCD2Function(catalog_name, db_name, table_name_stage, table_name_dim,
                      catalog_source, db_name_source, table_name_source, column_names)

        # Check that the sql method was called with the correct arguments
        mock_sql.assert_any_call(f"use catalog {catalog_name}")
        mock_sql.assert_any_call(f"use schema {db_name}")
        mock_sql.assert_any_call(f"DROP TABLE IF EXISTS {table_name_stage};")
        
        # Check the CREATE TABLE statement
        column_definitions = ", ".join([f"{col} STRING" for col in column_names])
        mock_sql.assert_any_call(f"CREATE TABLE IF NOT EXISTS {table_name_stage} ({column_definitions}) USING DELTA;")
        
        # Check TRUNCATE statement
        mock_sql.assert_any_call(f"TRUNCATE TABLE {table_name_stage};")
        
        # Check INSERT statement
        insert_query = f"INSERT INTO {table_name_stage} SELECT " + ", ".join([f"TRY_CAST({col} AS STRING)" for col in column_names]) + f" FROM {catalog_source}.{db_name_source}.{table_name_source};"
        mock_sql.assert_any_call(insert_query)

        # Check the MERGE statement
        expected_merge_query = f"""
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
                    {' OR '.join([f'a.{col} != b.{col}' for col in column_names[1:]])}
                )
            ) b 
            ON a.{column_names[0]} = b.mergeKey and a.{column_names[-1]}='active'
            WHEN MATCHED AND (
                {' OR '.join([f'b.{col} != a.{col}' for col in column_names[1:]])}
            ) THEN 
                UPDATE SET 
                    {column_names[-1]} = 'inactive',
                    a.end_date = current_date() - 1 
            WHEN NOT MATCHED THEN 
                INSERT ({', '.join(column_names)}, start_date, end_date) 
                VALUES ({', '.join(column_names)}, current_date(), '9999-12-31');
        """.strip()  # Remove leading/trailing whitespace

        # Normalize whitespace in the actual query
        actual_merge_calls = [call[0][0] for call in mock_sql.call_args_list if "MERGE INTO" in call[0][0]]
        self.assertTrue(actual_merge_calls, "No MERGE calls found.")
        
        for actual_query in actual_merge_calls:
            normalized_actual = ' '.join(actual_query.split())
            normalized_expected = ' '.join(expected_merge_query.split())
            self.assertEqual(normalized_actual, normalized_expected)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
