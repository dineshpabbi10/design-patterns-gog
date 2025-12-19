# Composite Pattern

## Problem

Your **orchestration layer** must execute **hierarchical operations** composed of many smaller sub-operations:

* **Bulk updates** spanning multiple microservices
* **Fan-out workflows** (user-service → billing → inventory → notifications)
* **Long-running batches** with partial progress tracking
* **Parallel or sequential execution** depending on the operation

Each operation may:

* Succeed or fail independently
* Run in parallel or sequence
* Be cancelled mid-flight
* Report partial progress and aggregated errors

### Without Composite

You end up with **special-case orchestration logic** everywhere:

```python
# ❌ Hard-coded orchestration logic
def bulk_update():
    user_result = update_user()
    if not user_result.success:
        return failure()

    inventory_result = update_inventory()
    billing_result = update_billing()

    if inventory_result.failed or billing_result.failed:
        return partial_failure()
```

**Problems:**

* Tight coupling between orchestration and execution logic
* No recursive composition
* Hard to parallelize
* Difficult to track progress or aggregate failures
* Adding nested workflows becomes unmanageable

---

## Solution

Use the **Composite Pattern** to model **operations as a tree**:

* **LeafOperation** → Executes a single RPC / task
* **CompositeOperation** → Executes and aggregates child operations
* **Operation interface** → Uniform execution, cancellation, and status tracking

This allows:

* Recursive composition
* Parallel or sequential execution
* Aggregated success/failure
* Partial execution and progress reporting
* Transparent orchestration

---

## Core Design

```python
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
```

### Operation Status

```python
class OperationStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
```

---

### Operation Result

```python
class OperationResult:
    def __init__(self, status=OperationStatus.PENDING, errors=None):
        self.status = status
        self.errors = errors if errors else []

    @property
    def is_complete(self):
        return self.status in {OperationStatus.SUCCESS, OperationStatus.FAILURE}
```

---

### Component Interface

```python
class Operation(ABC):
    @abstractmethod
    def execute(self) -> OperationResult:
        pass

    @abstractmethod
    def cancel(self) -> None:
        pass

    @abstractmethod
    def get_status(self) -> OperationStatus:
        pass
```

---

## Leaf Operation

Represents a **single RPC / microservice call**.

```python
class LeafOperation(Operation):
    def __init__(self, name: str, payload: dict, fail: bool = False):
        self.name = name
        self.payload = payload
        self.fail = fail
        self.result = OperationResult()

    def execute(self) -> OperationResult:
        try:
            self.result.status = OperationStatus.IN_PROGRESS
            time.sleep(0.5)  # simulate RPC latency

            if self.fail:
                raise Exception(f"{self.name} failed")

            self.result.status = OperationStatus.SUCCESS
            return self.result

        except Exception as e:
            self.result.status = OperationStatus.FAILURE
            self.result.errors.append(e)
            return self.result

    def cancel(self):
        if self.result.status == OperationStatus.IN_PROGRESS:
            self.result.status = OperationStatus.FAILURE

    def get_status(self):
        return self.result.status
```

---

## Composite Operation

Executes and aggregates child operations.

```python
class CompositeOperation(Operation):
    def __init__(self, name: str, children: Optional[List[Operation]] = None, parallel=False):
        self.name = name
        self.children = children or []
        self.parallel = parallel
        self.result = OperationResult()

    def add_operation(self, operation: Operation):
        self.children.append(operation)
```

---

### Sequential Execution

```python
    def _execute_sequential(self):
        self.result.status = OperationStatus.IN_PROGRESS
        success = True

        for child in self.children:
            result = child.execute()
            if result.status == OperationStatus.FAILURE:
                success = False
                self.result.errors.extend(result.errors)

        self.result.status = OperationStatus.SUCCESS if success else OperationStatus.FAILURE
        return self.result
```

---

### Parallel Execution

```python
    def _execute_parallel(self):
        self.result.status = OperationStatus.IN_PROGRESS
        success = True

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(child.execute) for child in self.children]

            for future in as_completed(futures):
                result = future.result()
                if result.status == OperationStatus.FAILURE:
                    success = False
                    self.result.errors.extend(result.errors)

        self.result.status = OperationStatus.SUCCESS if success else OperationStatus.FAILURE
        return self.result
```

---

### Unified Execution API

```python
    def execute(self):
        return (
            self._execute_parallel()
            if self.parallel
            else self._execute_sequential()
        )

    def cancel(self):
        for child in self.children:
            child.cancel()
        self.result.status = OperationStatus.FAILURE

    def get_status(self):
        if all(c.get_status() == OperationStatus.SUCCESS for c in self.children):
            return OperationStatus.SUCCESS
        if any(c.get_status() == OperationStatus.FAILURE for c in self.children):
            return OperationStatus.FAILURE
        if any(c.get_status() == OperationStatus.IN_PROGRESS for c in self.children):
            return OperationStatus.IN_PROGRESS
        return OperationStatus.PENDING
```

---

### Progress Tracking

```python
    def get_progress(self) -> float:
        if not self.children:
            return 100.0
        completed = sum(1 for c in self.children if c.result.is_complete)
        return (completed / len(self.children)) * 100
```

---

## Usage Example: Bulk Update Workflow

```python
bulk_update = CompositeOperation(
    name="bulk-update",
    parallel=True,
    children=[
        LeafOperation("user-service", {"user_id": 1}),
        LeafOperation("inventory-service", {"sku": "A1"}, fail=True),
        LeafOperation("billing-service", {"invoice": 123}),
    ],
)

bulk_update.execute()

print("Status:", bulk_update.get_status().value)
print("Progress:", bulk_update.get_progress(), "%")
print("Errors:", bulk_update.result.errors)
```

---

## Recursive Composition (Nested Workflows)

```python
billing_flow = CompositeOperation(
    "billing-flow",
    children=[
        LeafOperation("invoice"),
        LeafOperation("payment"),
    ]
)

root = CompositeOperation(
    "root-workflow",
    parallel=True,
    children=[
        LeafOperation("user-service"),
        billing_flow,
        LeafOperation("notification-service"),
    ],
)

root.execute()
```

---

## Concurrency & Orchestration

* Parallel execution via `ThreadPoolExecutor`
* Compatible with:

  * Worker pools
  * Background job schedulers
  * Async orchestration layers
* Supports **best-effort execution** (all children run even if some fail)

---

## Testing Example

```python
def test_partial_failure():
    op = CompositeOperation(
        "test",
        children=[
            LeafOperation("ok"),
            LeafOperation("fail", fail=True),
        ],
    )

    result = op.execute()
    assert result.status == OperationStatus.FAILURE
    assert len(result.errors) == 1
```

---

## Benefits

| Pros                                              | Cons                               |
| ------------------------------------------------- | ---------------------------------- |
| Uniform interface for simple & complex operations | More abstraction                   |
| Recursive composition                             | Requires careful state handling    |
| Parallel & sequential execution                   | Thread cancellation is cooperative |
| Aggregated errors                                 | Retry logic not built-in           |
| Progress tracking                                 |                                    |

---

## Advanced Extensions

* **Retry Decorator** for operations
* **Fail-fast vs best-effort policies**
* **Compensation / rollback operations**
* **Timeout-aware execution**
* **Tracing & metrics decorators**
* **Async (`asyncio`) implementation**

---

## When to Use Composite

✅ Use when:

* Operations naturally form trees
* You need uniform handling of single and grouped actions
* Orchestration logic must remain clean

❌ Avoid when:

* Execution order is strictly linear
* No hierarchical grouping exists
