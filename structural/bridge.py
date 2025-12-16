"""
Problem: Your data platform needs to ingest large volumes of customer and transaction data into multiple storage backends depending on deployment context:

**Production Environment**: Apache Spark ETL jobs write processed data to S3 (AWS data lake)
**Multi-cloud Strategy**: Same ETL logic needs to write to Google Cloud Storage (GCS) for enterprises on Google Cloud
**Local Development**: Engineers need to test without AWS credentials; data goes to local filesystem
**Testing/CI**: Automated tests should use in-memory mock storage instead of real cloud services

Currently, your ingestion logic is tightly coupled to specific storage implementations. Your `SparkJobSpec`-built ETL pipeline contains conditionals like:

```python
# ❌ Current approach: storage backend logic mixed into ingestion
def execute_etl(job_spec, backend_type):
    # ... data processing logic ...
    
    if backend_type == "s3":
        boto3.client("s3").put_object(Bucket="data-lake", Key="output", Body=processed_data)
    elif backend_type == "gcs":
        gcs.Client().bucket("data-lake").blob("output").upload_from_string(processed_data)
    elif backend_type == "local":
        with open("/data/output", "wb") as f:
            f.write(processed_data)
    elif backend_type == "mock":
        mock_storage[key] = processed_data
```

**Problems with this approach:**
1. **Tight Coupling**: Adding a new backend (e.g., Azure Blob Storage) requires modifying the `execute_etl` function
2. **Hard to Test**: Unit tests must mock multiple boto3/gcs client calls or use real credentials
3. **Code Duplication**: Ingestion logic is repeated for each backend variant
4. **Maintenance Nightmare**: A bug fix in the ingestion algorithm must be applied in every backend branch
5. **Performance Issues**: Different backends have different optimization strategies (buffering, batching, retry logic)

**Example Real Scenario:**
Your team deployed with S3 backend. Now a customer wants their data in GCS. You're forced to:
- Duplicate the entire `execute_etl` function for GCS
- Risk inconsistencies between S3 and GCS versions
- Write duplicate tests for each backend

**Solution: Bridge Pattern**

Decouple the **Abstraction** (ingestion logic and job orchestration) from **Implementations** (storage backends):

- **Abstraction Layer**: `IngestJob` - contains business logic for data transformation, batching, error handling
- **Implementation Layer**: `StorageBackend` interface - defines how to write/read data
- **Concrete Implementations**: `S3Storage`, `GCSStorage`, `LocalStorage`, `MockStorage`

The bridge allows:
- ✅ Ingestion logic to remain unchanged regardless of storage backend
- ✅ New backends to be added without touching existing code
- ✅ Easy testing with mock storage
- ✅ Runtime backend selection based on configuration
- ✅ Team A uses S3, Team B uses GCS, same codebase

**Constraints & hints:**
- **Performance**: New storage backends should be pluggable without copying/converting data in ingestion logic
- **Error Handling**: Different backends have different failure modes (network timeouts vs file permissions); abstraction should handle gracefully
- **Monitoring**: Each backend needs different metrics (S3: put_object latency, Local: disk I/O, GCS: API quotas)
- **Configuration**: Backend should be injectable at runtime, not hardcoded (e.g., from `SparkJobSpec` or environment)
- **Idempotency**: Backends must support idempotent writes for fault-tolerance (important for distributed ETL)

**Deliverable:**
1. Define a `StorageBackend` abstract interface with methods for write/read/exists/delete operations
2. Implement concrete backends: `S3Storage`, `GCSStorage`, `LocalStorage`, `MockStorage`
3. Implement `IngestJob` abstraction that accepts a `StorageBackend` via constructor injection
4. Show how the same ingestion logic works with different backends at runtime
5. Demonstrate usage in production (S3), testing (Mock), and development (Local) scenarios
"""

from abc import ABC, abstractmethod
from threading import Lock
class StorageBackend(ABC):
    @abstractmethod
    def write(self, key: str, data: bytes):
        raise NotImplementedError("write method not implemented")

    @abstractmethod
    def update(self, key: str, data: bytes):
        raise NotImplementedError("update method not implemented")
    
    @abstractmethod
    def read(self, key: str) -> bytes:
        """
        Read data from the backend.
        
        Args:
            key (str): The key or identifier for the data to read.
        Returns:
            bytes: The data read from the backend.
        """
        raise NotImplementedError("read method not implemented")
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if data exists in the backend.

        Args:
            key (str): The key or identifier for the data to check.
        Returns:
            bool: True if the data exists, False otherwise.
        """
        raise NotImplementedError("exists method not implemented")
    
    @abstractmethod
    def delete(self, key: str):
        """Delete data from the backend.
        Args:
            key (str): The key or identifier for the data to delete.
        """
        raise NotImplementedError("delete method not implemented")


class S3Storage(StorageBackend):
    update_lock = Lock()
    def __init__(self, bucket_name: str):
        import boto3
        self.s3_client = boto3.client("s3")
        self.bucket_name = bucket_name

    def write(self, key: str, data: bytes):
        with self.update_lock:
            if(not self.exists(key)):
                self.s3_client.put_object(Bucket=self.bucket_name, Key=key, Body=data)
            else:
                print(f"Data with key {key} already exists in S3. Skipping write.")

    def update(self, key: str, data: bytes):
        with self.update_lock:
            if(self.exists(key)):
                self.s3_client.put_object(Bucket=self.bucket_name, Key=key, Body=data)
            else:
                raise KeyError(f"Key {key} does not exist in S3. Cannot update non-existent key.")

    def read(self, key: str) -> bytes:
        response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
        return response['Body'].read()

    def exists(self, key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except self.s3_client.exceptions.NoSuchKey:
            return False

    def delete(self, key: str):
        with self.update_lock:
            if(self.exists(key)):
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)


class LocalStorage(StorageBackend):
    update_lock = Lock()

    def __init__(self, base_path: str):
        import os
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def write(self, key: str, data: bytes):
        with self.update_lock:
            if(not self.exists(key)):
                with open(f"{self.base_path}/{key}", "wb") as f:
                    f.write(data)
            else:
                print(f"Data with key {key} already exists in Local Storage. Skipping write.")

    def update(self, key: str, data: bytes):
        with self.update_lock:
            if(self.exists(key)):
                with open(f"{self.base_path}/{key}", "wb") as f:
                    f.write(data)
            else:
                raise KeyError(f"Key {key} does not exist in Local Storage. Cannot update non-existent key.")
            
    def read(self, key: str) -> bytes:
        with open(f"{self.base_path}/{key}", "rb") as f:
            return f.read()

    def exists(self, key: str) -> bool:
        import os
        return os.path.exists(f"{self.base_path}/{key}")

    def delete(self, key: str):
        with self.update_lock:
            if(self.exists(key)):
                import os
                os.remove(f"{self.base_path}/{key}")

class MockStorage(StorageBackend):
    update_lock = Lock()

    def __init__(self):
        self.storage = {}

    def write(self, key: str, data: bytes):
        with self.update_lock:
            if(not self.exists(key)):
                self.storage[key] = data
            else:
                print(f"Data with key {key} already exists in Mock Storage. Skipping write.")

    def update(self, key: str, data: bytes):
        with self.update_lock:
            if(self.exists(key)):
                self.storage[key] = data
            else:
                raise KeyError(f"Key {key} does not exist in Mock Storage. Cannot update non-existent key.")
            
    def read(self, key: str) -> bytes:
        return self.storage[key]

    def exists(self, key: str) -> bool:
        return key in self.storage

    def delete(self, key: str):
        with self.update_lock:
            if(self.exists(key)):
                del self.storage[key]

class GCSStorage(StorageBackend):
    update_lock = Lock()
    def __init__(self, bucket_name: str):
        from google.cloud import storage
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def write(self, key: str, data: bytes):
        with self.update_lock:
            if(not self.exists(key)):
                blob = self.bucket.blob(key)
                blob.upload_from_string(data)
            else:
                print(f"Data with key {key} already exists in GCS Storage. Skipping write.")

    def update(self, key: str, data: bytes):
        with self.update_lock:
            if(self.exists(key)):
                blob = self.bucket.blob(key)
                blob.upload_from_string(data)
            else:
                raise KeyError(f"Key {key} does not exist in GCS Storage. Cannot update non-existent key.")

    def read(self, key: str) -> bytes:
        blob = self.bucket.blob(key)
        return blob.download_as_bytes()

    def exists(self, key: str) -> bool:
        blob = self.bucket.blob(key)
        return blob.exists()

    def delete(self, key: str):
        with self.update_lock:
            if(self.exists(key)):
                blob = self.bucket.blob(key)
                blob.delete()

class IngestJob:
    def __init__(self, backend: "StorageBackend"):
        self.backend = backend

    def execute(self, data_key: str, data: bytes):
        # Example ingestion logic
        if not self.backend.exists(data_key):
            self.backend.write(data_key, data)
        else:
            print(f"Data with key {data_key} already exists. Skipping write.")


# Example usage:
local_backend = LocalStorage("/tmp/data")
ingest_job = IngestJob(local_backend)
ingest_job.execute("example_key", b"sample data")
mock_backend = MockStorage()
ingest_job_mock = IngestJob(mock_backend)
ingest_job_mock.execute("example_key", b"sample data in mock")

# Multi threaded access test with logging
import threading
import time

def ingest_with_log(backend: StorageBackend, key: str, data: bytes, thread_id: int):
    """Ingest with thread logging."""
    print(f"  Thread-{thread_id}: Starting write to '{key}'")
    start = time.time()
    job = IngestJob(backend)
    job.execute(key, data)
    elapsed = (time.time() - start) * 1000
    print(f"  Thread-{thread_id}: Completed in {elapsed:.2f}ms")

print("\n--- Threading Test: 5 threads writing to same key ---")
concurrent_mock = MockStorage()
threads = []
start_time = time.time()

for i in range(5):
    t = threading.Thread(target=ingest_with_log, args=(concurrent_mock, "shared_key", b"data", i))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

total_time = (time.time() - start_time) * 1000
print(f"Total time: {total_time:.2f}ms")
print(f"Final data in storage: {list(concurrent_mock.storage.keys())}")

### Pytest for the Bridge Pattern Implementation
def test_local_storage_write_read_delete():
    backend = LocalStorage("/tmp/test_data")
    key = "test_key"
    data = b"test data"

    backend.write(key, data)
    assert backend.exists(key) == True
    read_data = backend.read(key)
    assert read_data == data
    backend.delete(key)
    assert backend.exists(key) == False

def test_mock_storage_write_read_delete():
    backend = MockStorage()
    key = "test_key"
    data = b"test data"
    backend.write(key, data)
    assert backend.exists(key) == True
    read_data = backend.read(key)
    assert read_data == data
    backend.delete(key)
    assert backend.exists(key) == False

# Test class IngestJob:
def test_ingest_job_with_mock_storage():
    backend = MockStorage()
    ingest_job = IngestJob(backend)
    key = "ingest_key"
    data = b"ingest data"
    ingest_job.execute(key, data)
    assert backend.exists(key) == True
    read_data = backend.read(key)
    assert read_data == data
    ingest_job.execute(key, data)  # Should skip write
    assert backend.exists(key) == True
    ingest_job = IngestJob(backend)
    backend.delete(key)
    assert backend.exists(key) == False