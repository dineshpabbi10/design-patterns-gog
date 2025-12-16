"""
Problem: Design a process-local, thread-safe singleton `ParagoNClientManager` that provides a single cached instance
of a `ParagoNClient` (or similar third-party client) for a microservice process. The manager must lazily initialize
credentials, handle token refresh safely under concurrency, and expose a simple API for obtaining the client.

Constraints & hints:
- Your microservices run multiple threads and may spawn worker threads for async tasks.
- The client should be usable by both request-handling code and background jobs.
- Consider lazy init, double-checked locking, and safe cleanup on shutdown.

Deliverable: implement the singleton pattern in `ParagoNClientManager` so other modules import a single instance.
"""
from threading import Lock
import time

class ParagonNSingleton:
    _instance = None
    _lock = Lock()

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.token = 0
    
    def _fetch_token(self) -> int:
        # Simulate fetching a token using the API key
        with self._lock:
        # time.sleep(0.5)  # Simulate network delay
            self.token += 1
            return self.token

    def refresh_token(self):
        self.token = self._fetch_token()
        return self.token



class ParagonNSingletonManager:
    _instance = None 
    _lock = Lock()

    def __new__(cls,*args,**kwargs):
        raise NotImplementedError("Use get_instance() method to get the singleton instance.")

    @classmethod 
    def get_instance(cls, api_key: str) -> "ParagonNSingletonManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(ParagonNSingletonManager)
                    cls._instance.client = ParagonNSingleton(api_key)
        return cls._instance
    
    @classmethod
    def get_client(cls, api_key: str) -> ParagonNSingleton:
        instance = cls.get_instance(api_key)
        return instance.client


a = ParagonNSingletonManager.get_client("my_api_key")
b = ParagonNSingletonManager.get_client("my_api_key")


print(a is b)  # Should print True, confirming both are the same instance

# Test multi-threaded access
def access_client():
    client = ParagonNSingletonManager.get_client("my_api_key")
    print(f"Accessed client")
    client.refresh_token()
    print(f"Refreshed token: {client.token}")

import threading

threads = []
for i in range(5):
    t = threading.Thread(target=access_client)
    threads.append(t)
    t.start()

for t in threads:
    t.join()

