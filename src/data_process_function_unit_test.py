import unittest
from unittest.mock import patch
from pyspark.dbutils import DBUtils

def setup_streaming_pipeline(spark, catalog_name, bronze_db, silver_db, bronze_table, silver_table, eventHubName, key_vault, connector, checkpoint_base_path, json_schema, explode_field=None):
    # Initialize DBUtils
    dbutils = DBUtils(spark)

    # Set up widgets and paths
    dbutils.widgets.dropdown("trigger_available_now", "False", ["True", "False"])
    
    notebook_name = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get().split("/")[-1].split(".")[0]
    bronze_checkpoint_path = f"{checkpoint_base_path}/{catalog_name}/{bronze_db}/checkpoints/{notebook_name}/"
    silver_checkpoint_path = f"{checkpoint_base_path}/{catalog_name}/{silver_db}/checkpoints/{notebook_name}/"

    # Catalog and schema setup
    try:
        spark.sql(f"CREATE CATALOG IF NOT EXISTS {catalog_name} MANAGED LOCATION 'abfss://streamingdata-demo@dataengineerdemoweather.dfs.core.windows.net/';")
    except Exception:
        print('Catalog might already exist.')

    for db in [bronze_db, silver_db]:
        try:
            spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog_name}.{db};")
        except Exception:
            print(f"{db} schema might already exist.")

    for db, path in [(bronze_db, bronze_checkpoint_path), (silver_db, silver_checkpoint_path)]:
        try:
            spark.sql(f"CREATE VOLUME IF NOT EXISTS {catalog_name}.{db}.checkpoints;")
        except Exception:
            print(f"{db} checkpoints might already exist.")

    connectionString = dbutils.secrets.get(key_vault, connector)
    ehConf = {
        'eventhubs.connectionString': spark._jvm.org.apache.spark.eventhubs.EventHubsUtils.encrypt(connectionString),
        'eventhubs.eventHubName': eventHubName
    }
    return ehConf  # Return the configuration for testing purposes

class TestStreamingPipeline(unittest.TestCase):

    @patch('pyspark.dbutils.DBUtils')
    @patch('pyspark.sql.SparkSession')
    def test_setup_streaming_pipeline(self, MockSparkSession, MockDBUtils):
        # Create a local Spark session mock
        spark = MockSparkSession.builder.getOrCreate.return_value

        # Mock DBUtils and its methods
        mock_dbutils = MockDBUtils.return_value
        mock_dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get.return_value = "test_notebook"

        # Call the function
        setup_streaming_pipeline(
            spark,
            catalog_name="test_catalog",
            bronze_db="test_bronze",
            silver_db="test_silver",
            bronze_table="bronze_table",
            silver_table="silver_table",
            eventHubName="eventHub",
            key_vault="testScope1",
            connector="testsecrettyler",
            checkpoint_base_path="/checkpoints",
            json_schema="schema",
            explode_field=None
        )

        # Assertions for expected SQL calls
        spark.sql.assert_any_call("CREATE CATALOG IF NOT EXISTS test_catalog MANAGED LOCATION 'abfss://streamingdata-demo@dataengineerdemoweather.dfs.core.windows.net/';")
        spark.sql.assert_any_call("CREATE SCHEMA IF NOT EXISTS test_catalog.test_bronze;")
        spark.sql.assert_any_call("CREATE SCHEMA IF NOT EXISTS test_catalog.test_silver;")
        spark.sql.assert_any_call("CREATE VOLUME IF NOT EXISTS test_catalog.test_bronze.checkpoints;")
        spark.sql.assert_any_call("CREATE VOLUME IF NOT EXISTS test_catalog.test_silver.checkpoints;")

    @patch('pyspark.dbutils.DBUtils')
    @patch('pyspark.sql.SparkSession')
    def test_setup_streaming_pipeline_with_mocked_secrets(self, MockSparkSession, MockDBUtils):
        # Arrange
        mock_spark = MockSparkSession.builder.getOrCreate.return_value
        mock_dbutils = MockDBUtils.return_value
        mock_dbutils.secrets.get.return_value = "fake_connection_string"

        eventHubName = "test_eventhub"
        key_vault = "testScope1"
        connector = "testsecrettyler"
        catalog_name = "test_catalog"
        bronze_db = "test_bronze"
        silver_db = "test_silver"
        checkpoint_base_path = "/checkpoints"
        json_schema = "schema"

        # Act
        result = setup_streaming_pipeline(mock_spark, catalog_name, bronze_db, silver_db, None, None, eventHubName, key_vault, connector, checkpoint_base_path, json_schema)

        # Assert
        self.assertIsNotNone(result)
        self.assertIn('eventhubs.connectionString', result)
        self.assertIn('eventhubs.eventHubName', result)
        self.assertEqual(result['eventhubs.eventHubName'], eventHubName)
        self.assertEqual(result['eventhubs.connectionString'], 
                         mock_spark._jvm.org.apache.spark.eventhubs.EventHubsUtils.encrypt("fake_connection_string"))


if __name__ == '__main__':
    # Create a test suite
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestStreamingPipeline))
    
    # Run the test suite
    runner = unittest.TextTestRunner()
    runner.run(suite)
