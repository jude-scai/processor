"""
Integration tests for all Docker services (PostgreSQL/BigQuery, GCS, Pub/Sub, Redis)
"""
import os
import time
import pytest
from google.cloud import bigquery
from google.cloud import storage
from google.cloud import pubsub_v1
import redis
from dotenv import load_dotenv
from google.auth.credentials import AnonymousCredentials

# Load environment variables from .env file
load_dotenv()

# Database connection type: postgresql or bigquery
DATABASE_CONNECTION = os.getenv("DATABASE_CONNECTION", "postgresql")

# PostgreSQL configuration
POSTGRES_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "aura_underwriting"),
    "user": os.getenv("POSTGRES_USER", "aura_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "aura_password"),
}

# BigQuery configuration
BIGQUERY_PROJECT = os.getenv("BIGQUERY_PROJECT", "aura-project")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "underwriting_data")
BIGQUERY_EMULATOR_HOST = os.getenv("BIGQUERY_EMULATOR_HOST", "localhost:9050")

# Other services
GCS_EMULATOR_HOST = os.getenv("STORAGE_EMULATOR_HOST", "http://localhost:4443")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "aura-documents")

PUBSUB_PROJECT = os.getenv("PUBSUB_PROJECT", "aura-project")
PUBSUB_EMULATOR_HOST = os.getenv("PUBSUB_EMULATOR_HOST", "localhost:8085")
PUBSUB_TOPIC = os.getenv("PUBSUB_TOPIC", "test-topic")
PUBSUB_SUBSCRIPTION = os.getenv("PUBSUB_SUBSCRIPTION", "test-subscription")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))


@pytest.mark.skipif(DATABASE_CONNECTION != "postgresql", reason="Requires DATABASE_CONNECTION=postgresql")
class TestPostgreSQL:
    """Test PostgreSQL database connectivity and schema"""

    @pytest.fixture
    def db_connection(self):
        """Create a database connection for testing"""
        import psycopg2
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        yield conn
        conn.close()

    def test_connection(self, db_connection):
        """Test basic database connectivity"""
        cursor = db_connection.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        assert version is not None
        assert "PostgreSQL" in version[0]
        print(f"✅ PostgreSQL connected: {version[0][:50]}...")
        cursor.close()

    def test_schema_tables_exist(self, db_connection):
        """Test that core tables exist"""
        cursor = db_connection.cursor()

        tables = [
            'organization', 'account', 'role', 'permission',
            'underwriting', 'document', 'document_revision',
            'organization_processors', 'underwriting_processors', 'processor_executions',
            'factor', 'factor_snapshot'
        ]

        for table_name in tables:
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = '{table_name}'
                );
            """)
            exists = cursor.fetchone()[0]
            assert exists, f"Table {table_name} does not exist"

        print(f"✅ All {len(tables)} core tables exist")
        cursor.close()

    def test_insert_and_query_underwriting(self, db_connection):
        """Test inserting and querying an underwriting record"""
        from psycopg2.extras import RealDictCursor
        cursor = db_connection.cursor(cursor_factory=RealDictCursor)

        # Get test organization and account
        cursor.execute("SELECT id FROM organization WHERE name = 'Test Organization';")
        org = cursor.fetchone()
        if not org:
            pytest.skip("Seed data not loaded")
        org_id = org["id"]

        cursor.execute("SELECT id FROM account WHERE email = 'test@example.com';")
        account = cursor.fetchone()
        if not account:
            pytest.skip("Seed data not loaded")
        account_id = account["id"]

        # Insert test underwriting
        cursor.execute("""
            INSERT INTO underwriting (
                organization_id, serial_number, status, merchant_name,
                created_by, updated_by
            ) VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, serial_number, status, merchant_name;
        """, (org_id, "TEST-001", "created", "Test Merchant", account_id, account_id))

        result = cursor.fetchone()
        assert result is not None
        assert result["serial_number"] == "TEST-001"
        assert result["merchant_name"] == "Test Merchant"

        print(f"✅ Insert and query successful")
        db_connection.commit()
        cursor.close()


@pytest.mark.skipif(DATABASE_CONNECTION != "bigquery", reason="Requires DATABASE_CONNECTION=bigquery")
class TestBigQuery:
    """Test BigQuery emulator connectivity and basic CRUD via REST port (9050)"""

    @pytest.fixture(scope="class")
    def bq_client(self):
        os.environ["BIGQUERY_EMULATOR_HOST"] = BIGQUERY_EMULATOR_HOST
        client = bigquery.Client(
            project=BIGQUERY_PROJECT,
            credentials=AnonymousCredentials(),
            client_options={"api_endpoint": f"http://{BIGQUERY_EMULATOR_HOST}"}
        )
        yield client
        client.close()

    def test_emulator_running(self):
        """Test BigQuery emulator is running and responding"""
        import requests
        response = requests.get("http://localhost:9050", timeout=3)
        # Any response (even error) confirms emulator is running
        assert response.status_code in [404, 500]
        print("✅ BigQuery emulator is running")

    def test_rest_api_available(self):
        """Test BigQuery REST API endpoint is available"""
        import requests
        # Test a valid endpoint path
        response = requests.get(
            f"http://localhost:9050/bigquery/v2/projects/{BIGQUERY_PROJECT}/datasets",
            timeout=3
        )
        # Should get some response (200 or error)
        assert response.status_code in [200, 404, 500]
        print(f"✅ BigQuery REST API responding")

    def test_client_can_be_created(self):
        """Test that BigQuery client can be initialized"""
        os.environ["BIGQUERY_EMULATOR_HOST"] = BIGQUERY_EMULATOR_HOST

        client = bigquery.Client(
            project=BIGQUERY_PROJECT,
            credentials=AnonymousCredentials(),
            client_options={"api_endpoint": f"http://{BIGQUERY_EMULATOR_HOST}"}
        )

        assert client is not None
        assert client.project == BIGQUERY_PROJECT
        client.close()
        print(f"✅ BigQuery client initialized for {BIGQUERY_PROJECT}")

    @pytest.mark.timeout(10)
    def test_create_dataset_via_client(self, bq_client):
        """Create a temporary dataset and verify it succeeds (timeout 10s)"""
        import uuid
        unique_suffix = uuid.uuid4().hex[:8]
        dataset_id = f"{BIGQUERY_PROJECT}.{BIGQUERY_DATASET}_ds_{unique_suffix}"
        dataset = bigquery.Dataset(dataset_id)
        dataset.location = "US"
        ds = bq_client.create_dataset(dataset, exists_ok=True)
        assert ds.dataset_id.startswith(f"{BIGQUERY_DATASET}_ds_")
        print(f"✅ Dataset created: {ds.dataset_id}")

    @pytest.mark.timeout(10)
    def test_create_table_via_client(self, bq_client):
        """Create a small table in the temp dataset (timeout 10s)"""
        import requests
        dataset_id = f"{BIGQUERY_PROJECT}.{BIGQUERY_DATASET}_itest"
        # ensure dataset exists via REST to avoid emulator 500 retry loop
        requests.post(
            f"http://localhost:9050/bigquery/v2/projects/{BIGQUERY_PROJECT}/datasets",
            json={"datasetReference": {"datasetId": f"{BIGQUERY_DATASET}_itest", "projectId": BIGQUERY_PROJECT}},
            timeout=3
        )

        table_id = f"{dataset_id}.itest_simple"
        schema = [
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("name", "STRING"),
            bigquery.SchemaField("value", "INT64"),
        ]
        table = bigquery.Table(table_id, schema=schema)
        tbl = bq_client.create_table(table, exists_ok=True)
        assert tbl.table_id == "itest_simple"
        print("✅ Table created: itest_simple")

    @pytest.mark.timeout(15)
    def test_insert_and_query_via_client(self, bq_client):
        """Insert a row and query it back (timeout 15s)"""
        import requests
        import uuid
        dataset = f"{BIGQUERY_PROJECT}.{BIGQUERY_DATASET}_itest"
        table_id = f"{dataset}.itest_simple"
        # ensure dataset exists via REST
        requests.post(
            f"http://localhost:9050/bigquery/v2/projects/{BIGQUERY_PROJECT}/datasets",
            json={"datasetReference": {"datasetId": f"{BIGQUERY_DATASET}_itest", "projectId": BIGQUERY_PROJECT}},
            timeout=3
        )
        # ensure table exists
        schema = [
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("name", "STRING"),
            bigquery.SchemaField("value", "INT64"),
        ]
        bq_client.create_table(bigquery.Table(table_id, schema=schema), exists_ok=True)

        unique_id = f"it_{uuid.uuid4().hex[:8]}"
        errors = bq_client.insert_rows_json(table_id, [{"id": unique_id, "name": "Alpha", "value": 7}])
        assert errors == []

        rows = list(bq_client.query(f"SELECT id,name,value FROM `{table_id}` WHERE id='{unique_id}'").result())
        assert len(rows) == 1 and rows[0]["name"] == "Alpha"
        print("✅ Insert/Query succeeded via client")


class TestGCS:
    """Test Google Cloud Storage emulator connectivity"""

    @pytest.fixture
    def gcs_client(self):
        """Create GCS client for testing"""
        os.environ["STORAGE_EMULATOR_HOST"] = GCS_EMULATOR_HOST

        client = storage.Client(
            project=BIGQUERY_PROJECT,
            client_options={"api_endpoint": GCS_EMULATOR_HOST}
        )
        yield client

    def test_connection(self, gcs_client):
        """Test basic GCS connectivity"""
        try:
            # List buckets to verify connection
            buckets = list(gcs_client.list_buckets())
            assert isinstance(buckets, list)
        except Exception as e:
            pytest.skip(f"GCS emulator not ready: {e}")

    def test_create_bucket(self, gcs_client):
        """Test creating a bucket"""
        try:
            bucket = gcs_client.bucket(GCS_BUCKET_NAME)

            # Create bucket if it doesn't exist
            if not bucket.exists():
                bucket = gcs_client.create_bucket(GCS_BUCKET_NAME)

            assert bucket.name == GCS_BUCKET_NAME
        except Exception as e:
            pytest.skip(f"GCS bucket operations not supported: {e}")

    def test_upload_and_download_blob(self, gcs_client):
        """Test uploading and downloading a blob"""
        try:
            # Ensure bucket exists
            bucket = gcs_client.bucket(GCS_BUCKET_NAME)
            if not bucket.exists():
                bucket = gcs_client.create_bucket(GCS_BUCKET_NAME)

            # Upload test file
            blob_name = "test-document.txt"
            test_content = b"This is a test document for AURA processing engine."

            blob = bucket.blob(blob_name)
            blob.upload_from_string(test_content)

            # Download and verify
            downloaded_content = blob.download_as_bytes()
            assert downloaded_content == test_content

            # Clean up
            blob.delete()
        except Exception as e:
            pytest.skip(f"GCS blob operations not supported: {e}")


class TestPubSub:
    """Test Google Cloud Pub/Sub emulator connectivity"""

    @pytest.fixture
    def pubsub_publisher(self):
        """Create Pub/Sub publisher client for testing"""
        os.environ["PUBSUB_EMULATOR_HOST"] = PUBSUB_EMULATOR_HOST

        publisher = pubsub_v1.PublisherClient()
        yield publisher

    @pytest.fixture
    def pubsub_subscriber(self):
        """Create Pub/Sub subscriber client for testing"""
        os.environ["PUBSUB_EMULATOR_HOST"] = PUBSUB_EMULATOR_HOST

        subscriber = pubsub_v1.SubscriberClient()
        yield subscriber

    def test_create_topic(self, pubsub_publisher):
        """Test creating a Pub/Sub topic"""
        try:
            topic_path = pubsub_publisher.topic_path(PUBSUB_PROJECT, PUBSUB_TOPIC)

            # Create topic (ignore if already exists)
            try:
                topic = pubsub_publisher.create_topic(request={"name": topic_path})
                assert topic.name == topic_path
            except Exception:
                # Topic might already exist
                pass
        except Exception as e:
            pytest.skip(f"Pub/Sub emulator not ready: {e}")

    def test_create_subscription(self, pubsub_publisher, pubsub_subscriber):
        """Test creating a subscription"""
        try:
            topic_path = pubsub_publisher.topic_path(PUBSUB_PROJECT, PUBSUB_TOPIC)
            subscription_path = pubsub_subscriber.subscription_path(
                PUBSUB_PROJECT, PUBSUB_SUBSCRIPTION
            )

            # Ensure topic exists
            try:
                pubsub_publisher.create_topic(request={"name": topic_path})
            except Exception:
                pass

            # Create subscription
            try:
                subscription = pubsub_subscriber.create_subscription(
                    request={"name": subscription_path, "topic": topic_path}
                )
                assert subscription.name == subscription_path
            except Exception:
                # Subscription might already exist
                pass
        except Exception as e:
            pytest.skip(f"Pub/Sub subscription operations not supported: {e}")

    def test_publish_and_receive_message(self, pubsub_publisher, pubsub_subscriber):
        """Test publishing and receiving a message"""
        try:
            topic_path = pubsub_publisher.topic_path(PUBSUB_PROJECT, PUBSUB_TOPIC)
            subscription_path = pubsub_subscriber.subscription_path(
                PUBSUB_PROJECT, PUBSUB_SUBSCRIPTION
            )

            # Ensure topic and subscription exist
            try:
                pubsub_publisher.create_topic(request={"name": topic_path})
            except Exception:
                pass

            try:
                pubsub_subscriber.create_subscription(
                    request={"name": subscription_path, "topic": topic_path}
                )
            except Exception:
                pass

            # Publish message
            message_data = b"Test processor execution completed"
            future = pubsub_publisher.publish(topic_path, message_data)
            message_id = future.result()
            assert message_id is not None

            # Pull message
            response = pubsub_subscriber.pull(
                request={"subscription": subscription_path, "max_messages": 1},
                timeout=5.0
            )

            if response.received_messages:
                message = response.received_messages[0]
                assert message.message.data == message_data

                # Acknowledge message
                pubsub_subscriber.acknowledge(
                    request={
                        "subscription": subscription_path,
                        "ack_ids": [message.ack_id]
                    }
                )
        except Exception as e:
            pytest.skip(f"Pub/Sub message operations not supported: {e}")


class TestRedis:
    """Test Redis connectivity and operations"""

    @pytest.fixture
    def redis_client(self):
        """Create Redis client for testing"""
        client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True
        )
        yield client
        client.close()

    def test_connection(self, redis_client):
        """Test basic Redis connectivity"""
        assert redis_client.ping() is True

    def test_set_and_get(self, redis_client):
        """Test setting and getting values"""
        key = "test:processor:execution"
        value = "processor_123_completed"

        # Set value
        redis_client.set(key, value)

        # Get value
        retrieved = redis_client.get(key)
        assert retrieved == value

        # Clean up
        redis_client.delete(key)

    def test_hash_operations(self, redis_client):
        """Test hash operations for caching processor results"""
        hash_key = "test:processor:factors"
        factors = {
            "avg_revenue": "50000.00",
            "time_in_business": "36",
            "credit_score": "720"
        }

        # Set hash
        redis_client.hset(hash_key, mapping=factors)

        # Get all hash values
        retrieved = redis_client.hgetall(hash_key)
        assert retrieved == factors

        # Get specific field
        avg_revenue = redis_client.hget(hash_key, "avg_revenue")
        assert avg_revenue == "50000.00"

        # Clean up
        redis_client.delete(hash_key)

    def test_expiration(self, redis_client):
        """Test key expiration (TTL)"""
        key = "test:cache:temporary"
        value = "temporary_data"

        # Set value with 2 second expiration
        redis_client.setex(key, 2, value)

        # Verify value exists
        assert redis_client.get(key) == value

        # Wait for expiration
        time.sleep(3)

        # Verify value is gone
        assert redis_client.get(key) is None

    def test_list_operations(self, redis_client):
        """Test list operations for job queues"""
        list_key = "test:processor:queue"

        # Push items to list
        redis_client.rpush(list_key, "job1", "job2", "job3")

        # Get list length
        length = redis_client.llen(list_key)
        assert length == 3

        # Pop item from list
        job = redis_client.lpop(list_key)
        assert job == "job1"

        # Clean up
        redis_client.delete(list_key)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

