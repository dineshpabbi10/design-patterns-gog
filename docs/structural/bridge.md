# Bridge Pattern

## Problem

Your **ingestion logic** must support multiple storage backends:
- **Production**: S3 for large-scale data storage
- **Testing/Dev**: Local filesystem for quick iteration
- **Multi-cloud**: GCS for Google Cloud deployments

**Without Bridge**, you'd have conditional logic sprinkled everywhere:

```python
# ❌ Tight coupling to specific backends
def ingest_data(backend_type, data):
    if backend_type == "s3":
        s3 = boto3.client("s3")
        s3.put_object(Bucket="my-bucket", Key="data", Body=data)
    elif backend_type == "local":
        with open("/data/local", "wb") as f:
            f.write(data)
    elif backend_type == "gcs":
        gcs = storage.Client()
        bucket = gcs.bucket("my-bucket")
        blob = bucket.blob("data")
        blob.upload_from_string(data)
```

**Problem**: Ingestion logic is tightly coupled to storage implementation.

## Solution

Implement the bridge by separating the abstraction (ingestion logic) from implementations (storage backends):

```python
from abc import ABC, abstractmethod
from threading import Lock

# Implementation interface - storage backends
class StorageBackend(ABC):
    """Abstract interface for storage operations."""
    
    @abstractmethod
    def write(self, key: str, data: bytes):
        """Write data (idempotent - skips if exists)."""
        raise NotImplementedError("write method not implemented")

    @abstractmethod
    def update(self, key: str, data: bytes):
        """Update existing data (raises KeyError if not exists)."""
        raise NotImplementedError("update method not implemented")
    
    @abstractmethod
    def read(self, key: str) -> bytes:
        """Read data from the backend."""
        raise NotImplementedError("read method not implemented")
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if data exists in the backend."""
        raise NotImplementedError("exists method not implemented")
    
    @abstractmethod
    def delete(self, key: str):
        """Delete data from the backend."""
        raise NotImplementedError("delete method not implemented")


# Concrete Implementation: S3
class S3Storage(StorageBackend):
    """AWS S3 storage backend."""
    
    update_lock = Lock()
    
    def __init__(self, bucket_name: str):
        import boto3
        self.s3_client = boto3.client("s3")
        self.bucket_name = bucket_name

    def write(self, key: str, data: bytes):
        with self.update_lock:
            if not self.exists(key):
                self.s3_client.put_object(Bucket=self.bucket_name, Key=key, Body=data)
            else:
                print(f"Data with key {key} already exists in S3. Skipping write.")

    def update(self, key: str, data: bytes):
        with self.update_lock:
            if self.exists(key):
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
            if self.exists(key):
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)


# Concrete Implementation: Local Filesystem
class LocalStorage(StorageBackend):
    """Local filesystem storage backend."""
    
    update_lock = Lock()

    def __init__(self, base_path: str):
        import os
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def write(self, key: str, data: bytes):
        with self.update_lock:
            if not self.exists(key):
                with open(f"{self.base_path}/{key}", "wb") as f:
                    f.write(data)
            else:
                print(f"Data with key {key} already exists in Local Storage. Skipping write.")

    def update(self, key: str, data: bytes):
        with self.update_lock:
            if self.exists(key):
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
            if self.exists(key):
                import os
                os.remove(f"{self.base_path}/{key}")


# Concrete Implementation: Google Cloud Storage
class GCSStorage(StorageBackend):
    """Google Cloud Storage backend."""
    
    update_lock = Lock()
    
    def __init__(self, bucket_name: str):
        from google.cloud import storage
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)

    def write(self, key: str, data: bytes):
        with self.update_lock:
            if not self.exists(key):
                blob = self.bucket.blob(key)
                blob.upload_from_string(data)
            else:
                print(f"Data with key {key} already exists in GCS Storage. Skipping write.")

    def update(self, key: str, data: bytes):
        with self.update_lock:
            if self.exists(key):
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
            if self.exists(key):
                blob = self.bucket.blob(key)
                blob.delete()


# Concrete Implementation: In-memory Mock (for testing)
class MockStorage(StorageBackend):
    """In-memory mock storage for testing."""
    
    update_lock = Lock()

    def __init__(self):
        self.storage = {}

    def write(self, key: str, data: bytes):
        with self.update_lock:
            if not self.exists(key):
                self.storage[key] = data
            else:
                print(f"Data with key {key} already exists in Mock Storage. Skipping write.")

    def update(self, key: str, data: bytes):
        with self.update_lock:
            if self.exists(key):
                self.storage[key] = data
            else:
                raise KeyError(f"Key {key} does not exist in Mock Storage. Cannot update non-existent key.")
            
    def read(self, key: str) -> bytes:
        return self.storage[key]

    def exists(self, key: str) -> bool:
        return key in self.storage

    def delete(self, key: str):
        with self.update_lock:
            if self.exists(key):
                del self.storage[key]


# Abstraction: Ingestion Logic (independent of storage backend)
class IngestJob:
    """Ingestion job that works with any storage backend."""
    
    def __init__(self, backend: StorageBackend):
        self.backend = backend

    def execute(self, data_key: str, data: bytes):
        """Execute ingestion with idempotency check."""
        if not self.backend.exists(data_key):
            self.backend.write(data_key, data)
        else:
            print(f"Data with key {data_key} already exists. Skipping write.")
```

## Usage Examples

### Basic Usage: Production, Testing, and Development

```python
# Production: use S3
s3_backend = S3Storage(bucket_name="prod-data-lake")
ingest_job = IngestJob(s3_backend)
ingest_job.execute("2025-12-16/customer_data.parquet", b"production data")

# Local Development: use local filesystem
local_backend = LocalStorage("/tmp/data")
ingest_job_local = IngestJob(local_backend)
ingest_job_local.execute("example_key", b"sample data")

# Testing: use in-memory mock storage
mock_backend = MockStorage()
ingest_job_test = IngestJob(mock_backend)
ingest_job_test.execute("example_key", b"sample data in mock")

# Multi-cloud: use Google Cloud Storage
gcs_backend = GCSStorage(bucket_name="multi-cloud-data")
ingest_job_gcs = IngestJob(gcs_backend)
ingest_job_gcs.execute("2025-12-16/customer_data.parquet", b"gcs data")
```

### Demonstrating the Bridge: Same Logic, Different Backends

```python
# The key benefit: IngestJob logic is identical regardless of backend
def run_ingestion_pipeline(backend: StorageBackend, data_items: list):
    """Generic pipeline - works with ANY storage backend."""
    job = IngestJob(backend)
    for item in data_items:
        job.execute(item["key"], item["data"])
    print("Pipeline complete!")

# Use the same function with different backends
data = [
    {"key": "file1.txt", "data": b"content1"},
    {"key": "file2.txt", "data": b"content2"},
]

# Try with mock first
mock_backend = MockStorage()
run_ingestion_pipeline(mock_backend, data)

# Deploy with S3
s3_backend = S3Storage(bucket_name="my-bucket")
run_ingestion_pipeline(s3_backend, data)

# No code changes! Just swap the backend.
```

### Thread-Safe Updates with Write and Update Methods

```python
# Write: idempotent, skips if exists (used for initial writes)
backend = MockStorage()
backend.write("user:123", b'{"name": "Alice"}')  # Succeeds
backend.write("user:123", b'{"name": "Bob"}')    # Skips (already exists)

# Update: requires existing key (used for updates/patches)
try:
    backend.update("user:123", b'{"name": "Bob"}')  # Succeeds
    backend.update("user:999", b'{"name": "Charlie"}')  # Raises KeyError
except KeyError as e:
    print(f"Update failed: {e}")
```

### Concurrent Access with Lock Protection

```python
import threading

def ingest_in_thread(backend: StorageBackend, key: str, data: bytes):
    job = IngestJob(backend)
    job.execute(key, data)

# Test concurrent access with mock backend
mock_backend = MockStorage()
threads = []

for i in range(5):
    t = threading.Thread(
        target=ingest_in_thread, 
        args=(mock_backend, "concurrent_key", f"data_{i}".encode())
    )
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print(f"Final data in mock: {mock_backend.read('concurrent_key')}")
# All threads are synchronized via Lock - no race conditions
```

### Testing with Mock Backend

```python
# Unit test example - no need for real AWS/GCS credentials
def test_ingest_job_with_mock_storage():
    backend = MockStorage()
    ingest_job = IngestJob(backend)
    
    key = "ingest_key"
    data = b"ingest data"
    
    # Execute ingestion
    ingest_job.execute(key, data)
    assert backend.exists(key) == True
    
    # Verify data integrity
    read_data = backend.read(key)
    assert read_data == data
    
    # Test idempotency: second execute should skip
    ingest_job.execute(key, data)
    assert backend.exists(key) == True
    
    # Cleanup
    backend.delete(key)
    assert backend.exists(key) == False
```

## Benefits

| Pros | Cons |
|------|------|
| Decouple job logic from storage | Extra abstraction layers |
| Add new backends without changing job code | More code upfront |
| Easy to test with mock storage | Potential performance overhead |
| Swap backends at runtime | Interface mismatches between backends |
| Support multi-cloud deployments | |

## Advanced: Storage Factory

```python
def create_storage(backend_type: str, **config) -> StorageImplementation:
    """Factory for creating storage backends."""
    backends = {
        "s3": lambda: S3Storage(**config),
        "local": lambda: LocalStorage(**config),
        "gcs": lambda: GCSStorage(**config),
    }
    
    if backend_type not in backends:
        raise ValueError(f"Unknown storage backend: {backend_type}")
    
    return backends[backend_type]()

# Configuration-driven backend selection
backend_type = os.getenv("STORAGE_BACKEND", "s3")
storage = create_storage(backend_type, bucket_name="my-bucket")
job = IngestJob(storage, {"name": "my_job"})
```
