# Facade Pattern

## Problem

Your application includes a **complex onboarding subsystem** that must coordinate multiple internal and external services:

* **Identity service** (user creation)
* **Billing service** (subscription setup)
* **Third-party provider (ParagoN)** for provisioning
* **Error handling and compensation** when partial failures occur
* **Retry safety** for frontend and service retries

Each onboarding attempt may:

* Call multiple subsystems in a strict order
* Partially succeed and then fail
* Be retried due to network issues or client timeouts
* Require rollback of previously completed steps

### Without Facade

Controllers and callers end up containing **orchestration logic**:

```python
# ❌ Orchestration leaks into controllers
def onboard_user_controller(req):
    try:
        create_identity(req.user_id, req.email)
        create_subscription(req.user_id, req.plan_id)
        provision_paragon(req.user_id)
        return success()
    except Exception:
        rollback_billing(req.user_id)
        rollback_paragon(req.user_id)
        return failure()
```

**Problems:**

* Controllers become complex and fragile
* Orchestration logic is duplicated across callers
* Error recovery is inconsistent
* Retry behavior is unsafe without idempotency
* Changing onboarding steps requires touching many callers

---

## Solution

Use the **Facade Pattern** to provide a **single high-level API** for onboarding:

* **OnboardingFacade** → Orchestrates the full onboarding workflow
* **Subsystem services** → Identity, Billing, ParagoN
* **Idempotency store** → Ensures safe retries

The Facade:

* Hides orchestration details
* Centralizes error handling and rollback
* Returns a simple success/failure result
* Keeps controllers and frontends thin

---

## Core Design

```python
from dataclasses import dataclass
from typing import Optional, Dict
```

---

### Request DTO

Encapsulates all data needed for onboarding.

```python
@dataclass(frozen=True)
class OnboardUserRequest:
    user_id: str
    email: str
    plan_id: str
    idempotency_key: str
```

---

### Result DTO

Simple outcome returned to callers.

```python
@dataclass
class OnboardUserResult:
    success: bool
    user_id: Optional[str] = None
    error: Optional[str] = None
```

---

## Subsystem Services (Hidden Behind the Facade)

These represent **internal or external dependencies**.
The Facade coordinates them but callers never interact with them directly.

```python
class IdentityService:
    def create_user(self, user_id: str, email: str) -> None:
        ...
```

```python
class BillingService:
    def create_subscription(self, user_id: str, plan_id: str) -> None:
        ...
    def cancel_subscription(self, user_id: str) -> None:
        ...
```

```python
class ParagoNClient:
    def provision_account(self, user_id: str) -> None:
        ...
    def deprovision_account(self, user_id: str) -> None:
        ...
```

---

## Idempotency Store

Ensures **safe retries** by caching onboarding results.

```python
class IdempotencyStore:
    def __init__(self):
        self._store: Dict[str, OnboardUserResult] = {}

    def get(self, key: str) -> Optional[OnboardUserResult]:
        return self._store.get(key)

    def save(self, key: str, result: OnboardUserResult) -> None:
        self._store[key] = result
```

---

## Facade

Provides a **single entry point** for onboarding.

```python
class OnboardingFacade:
    """
    Facade that hides onboarding orchestration, retries, and recovery
    behind a single high-level API.
    """
```

---

### Orchestration Flow

```python
    def onboard_user(self, request: OnboardUserRequest) -> OnboardUserResult:
```

#### 1. Idempotency Check

```python
cached = self.idempotency_store.get(request.idempotency_key)
if cached:
    return cached
```

* Prevents duplicate onboarding
* Allows safe retries from frontend or services

---

#### 2. Execute Subsystems in Order

```python
self.identity.create_user(request.user_id, request.email)
self.billing.create_subscription(request.user_id, request.plan_id)
self.paragon.provision_account(request.user_id)
```

* Strict sequencing
* All orchestration is hidden from callers

---

#### 3. Error Handling & Compensation

```python
except Exception as e:
    self._rollback(request)
```

Rollback is **best-effort** and isolated:

```python
def _rollback(self, request: OnboardUserRequest) -> None:
    self.paragon.deprovision_account(request.user_id)
    self.billing.cancel_subscription(request.user_id)
```

---

#### 4. Persist Result

```python
self.idempotency_store.save(request.idempotency_key, result)
```

* Guarantees consistent results on retries

---

## Usage Example

### Controller / Caller

```python
result = facade.onboard_user(
    OnboardUserRequest(
        user_id="user-123",
        email="user@example.com",
        plan_id="pro",
        idempotency_key="req-001",
    )
)

if result.success:
    return 200
return 500
```

---

### Idempotent Retry

```python
result = facade.onboard_user(request)  # returns cached result
```

---

## Execution Characteristics

* **Sequential execution** of subsystems
* **Centralized rollback logic**
* **Idempotent retries**
* **Single return type for callers**

---

## Testing Example

```python
def test_idempotent_onboarding():
    result1 = facade.onboard_user(request)
    result2 = facade.onboard_user(request)
    assert result1 == result2
```

---

## Benefits

| Pros                      | Cons                       |
| ------------------------- | -------------------------- |
| Simple API for callers    | Facade can grow large      |
| Centralized orchestration | Requires careful design    |
| Consistent error handling | May hide subsystem details |
| Idempotent retry support  | Rollbacks are best-effort  |
| Keeps controllers thin    |                            |

---

## Advanced Extensions

* Persistent onboarding state machine
* Async / event-driven onboarding
* Saga-based compensation
* Retry & circuit breaker decorators
* Metrics and tracing inside Facade

---

## When to Use Facade

✅ Use when:

* Multiple subsystems must be coordinated
* Callers only care about success/failure
* Orchestration logic is growing in controllers
* You need a stable API over volatile internals

❌ Avoid when:

* Logic is trivial or single-service
* Callers need fine-grained control over steps
