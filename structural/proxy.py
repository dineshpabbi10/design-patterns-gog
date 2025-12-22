"""
Problem: Implement a `Proxy` for your HTTP API client that adds caching, rate-limiting, and circuit-breaker behavior in
front of `ParagoNClient`. The proxy should present the same API as the real client so callers can swap them easily.

Constraints & hints:
- Proxy must be transparent to callers (same method signatures).
- Support pluggable policies for caching TTL, rate limits, and breaker thresholds.
- Useful in edge services that aggregate third-party calls for frontends.

Deliverable: define the proxy interface and discuss policy configuration and metrics.
"""
import time

class ParagoNClient:
    def get_user(self, user_id: str) -> dict:
        # Simulate an API call to get user data
        print(f"Fetching user {user_id} from ParagoN API")
        return {"user_id": user_id, "name": "John Doe"}

    def update_user(self, user_id: str, data: dict) -> bool:
        # Simulate an API call to update user data
        print(f"Updating user {user_id} with data {data} in ParagoN API")
        return True

class ParagoNClientProxy:
    def __init__(self, client: ParagoNClient, cache_ttl: int = 60, rate_limit: int = 10, breaker_threshold: int = 5):
        self.client = client
        self.cache = {}
        self.cache_ttl = cache_ttl
        self.rate_limit = rate_limit
        self.breaker_threshold = breaker_threshold
        self.failure_count = 0
        self.last_failure_time = None

    def get_user(self, user_id: str) -> dict:
        current_time = time.time()

        # Circuit Breaker Logic
        if self.failure_count >= self.breaker_threshold:
            if current_time - self.last_failure_time < 60:  # 1 minute cooldown
                raise Exception("Circuit breaker is open. Request blocked.")
            else:
                self.failure_count = 0  # Reset after cooldown

        # Caching Logic
        if user_id in self.cache:
            cached_entry = self.cache[user_id]
            if current_time - cached_entry['timestamp'] < self.cache_ttl:
                print(f"Returning cached data for user {user_id}")
                return cached_entry['data']

        # Rate Limiting Logic (simple example)
        if len(self.cache) >= self.rate_limit:
            raise Exception("Rate limit exceeded. Try again later.")

        try:
            data = self.client.get_user(user_id)
            self.cache[user_id] = {'data': data, 'timestamp': current_time}
            return data
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = current_time
            raise e

    def update_user(self, user_id: str, data: dict) -> bool:
        current_time = time.time()

        # Circuit Breaker Logic
        if self.failure_count >= self.breaker_threshold:
            if current_time - self.last_failure_time < 60:  # 1 minute cooldown
                raise Exception("Circuit breaker is open. Request blocked.")
            else:
                self.failure_count = 0  # Reset after cooldown

        try:
            result = self.client.update_user(user_id, data)
            # Invalidate cache on update
            if user_id in self.cache:
                del self.cache[user_id]
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = current_time
            raise e


# Tests
def test_proxy_fast_circuit_breaker():
    client = ParagoNClient()
    proxy = ParagoNClientProxy(client, cache_ttl=2, rate_limit=4, breaker_threshold=2)

    # --- Test caching ---
    user1 = proxy.get_user("user1")
    user1_cached = proxy.get_user("user1")
    assert user1 == user1_cached

    time.sleep(3)  # Let cache expire
    user1_new = proxy.get_user("user1")
    assert user1 == user1_new  # Fresh fetch

    # --- Test rate limiting ---
    proxy.get_user("user2")
    try:
        proxy.get_user("user3")  # Should hit rate limit
    except Exception as e:
        assert str(e) == "Rate limit exceeded. Try again later."

    # --- Test circuit breaker ---
    original_get_user = client.get_user

    def failing_get_user(user_id: str):
        raise Exception("Simulated API failure")

    client.get_user = failing_get_user

    # Trigger failures
    try:
        proxy.get_user("user4")
    except Exception as e:
        assert str(e) == "Simulated API failure"

    try:
        proxy.get_user("user5")  # Should trip circuit breaker
    except Exception as e:
        assert str(e) == "Simulated API failure"

    # Simulate "time has passed" for circuit breaker cooldown
    fake_time = time.time()
    proxy.last_failure_time = fake_time - 61  # fast-forward 61 seconds

    # Restore working client
    client.get_user = original_get_user

    # Should succeed immediately without waiting
    user6 = proxy.get_user("user6")
    assert user6["user_id"] == "user6"

    print("All tests passed (fast circuit breaker).")