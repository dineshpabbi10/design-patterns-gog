# Proxy Pattern: HTTP API Client with Caching, Rate-Limiting, and Circuit Breaker

## Problem

Your **HTTP API client** (`ParagoNClient`) is used in edge services and frontends to fetch and update user data:

* Repeated API calls for the same user lead to **redundant network requests**
* High request rates can exceed **third-party API limits**
* Transient API failures may propagate to clients, causing downtime
* Managing caching, rate-limits, and circuit-breaking separately makes code **complex and scattered**

### Without Proxy

```python
# ❌ Direct client calls without policies
user = client.get_user("user123")
client.update_user("user123", {"plan": "pro"})
```

**Problems:**

* No caching → repeated fetches always hit the API
* No rate-limiting → risk of hitting API quotas
* No circuit breaker → failures propagate to callers
* Hard to add new policies without modifying client

---

## Solution

Use the **Proxy Pattern** to **wrap the original client** and provide **additional behaviors transparently**:

* **Caching** → store recent API responses to reduce repeated network calls
* **Rate-limiting** → prevent excessive API requests
* **Circuit breaker** → stop requests when failures exceed a threshold and allow recovery after cooldown
* **Transparent interface** → same method signatures as `ParagoNClient`, so callers can swap easily

This allows:

* Centralized policy enforcement
* Reduced API calls and latency
* Safe handling of transient failures
* Simplified client usage for frontends

---

## Core Design

```python
import time
```

### Proxy Class

```python
class ParagoNClientProxy:
    def __init__(self, client: ParagoNClient, cache_ttl: int = 60,
                 rate_limit: int = 10, breaker_threshold: int = 5):
        self.client = client
        self.cache = {}
        self.cache_ttl = cache_ttl
        self.rate_limit = rate_limit
        self.breaker_threshold = breaker_threshold
        self.failure_count = 0
        self.last_failure_time = None
```

* `client` → the real API client being wrapped
* `cache` → stores cached responses keyed by user ID
* `cache_ttl` → cache expiration time in seconds
* `rate_limit` → max number of concurrent requests in the cache
* `breaker_threshold` → number of failures before opening the circuit

---

### Caching Logic

```python
if user_id in self.cache:
    cached_entry = self.cache[user_id]
    if current_time - cached_entry['timestamp'] < self.cache_ttl:
        print(f"Returning cached data for user {user_id}")
        return cached_entry['data']
```

* Reduces repeated API calls for the same user
* TTL ensures cache freshness

---

### Rate-Limiting Logic

```python
if len(self.cache) >= self.rate_limit:
    raise Exception("Rate limit exceeded. Try again later.")
```

* Simple policy based on number of cached entries
* Prevents excessive load on the API

---

### Circuit Breaker Logic

```python
if self.failure_count >= self.breaker_threshold:
    if current_time - self.last_failure_time < 60:  # cooldown
        raise Exception("Circuit breaker is open. Request blocked.")
    else:
        self.failure_count = 0  # reset after cooldown
```

* Stops requests when failures exceed threshold
* Allows recovery after a cooldown period

---

### Unified Proxy API

```python
def get_user(self, user_id: str) -> dict:
    # Implements caching, rate-limiting, and circuit breaker
    ...
    
def update_user(self, user_id: str, data: dict) -> bool:
    # Implements circuit breaker and invalidates cache on update
    ...
```

* Methods **mirror the real client API**
* Transparent for callers

---

## Usage Example

```python
client = ParagoNClient()
proxy = ParagoNClientProxy(client, cache_ttl=60, rate_limit=10, breaker_threshold=5)

user = proxy.get_user("user123")  # Fetches from API
user_cached = proxy.get_user("user123")  # Returns cached
proxy.update_user("user123", {"plan": "pro"})  # Invalidates cache
```

---

## Testing Example (Fast Circuit Breaker)

```python
# Test caching, rate-limiting, and circuit breaker without real waits
test_proxy_fast_circuit_breaker()
```

* Uses **cache TTL of 2s** and **breaker threshold of 2**
* Simulates circuit breaker cooldown by **fast-forwarding last_failure_time**
* Tests **all proxy behaviors deterministically**

---

## Benefits

| Pros                                | Cons                              |
| ----------------------------------- | --------------------------------- |
| Transparent API proxy               | Adds some overhead per call       |
| Reduces redundant network requests  | Simple rate-limiting logic only   |
| Protects against cascading failures | Circuit breaker cooldown is fixed |
| Centralizes policy enforcement      | Not suitable for complex policies |

---

## Advanced Extensions

* Configurable **cache backends** (Redis, memcached)
* Pluggable **rate-limiting policies** (token bucket, leaky bucket)
* **Metrics collection** (success/failure counts, cache hits/misses)
* Async-friendly implementation using `asyncio`
* Dynamic **circuit breaker policies** per endpoint

---

## When to Use Proxy

✅ Use when:

* You want to add cross-cutting concerns like caching, throttling, or fault-tolerance
* You want **transparent client swapping** without changing callers
* You need centralized handling of third-party API calls

❌ Avoid when:

* No additional behavior is required beyond the client
* Overhead of proxy outweighs benefits for low-traffic services
