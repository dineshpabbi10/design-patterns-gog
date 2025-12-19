"""
Problem: You need to model hierarchical operations performed across services (e.g., a bulk-update composed of multiple
sub-requests to different microservices). Design a `Composite` structure where leaf operations execute RPCs and
composite nodes aggregate and run children.

Constraints & hints:
- Support recursive composition and aggregated success/failure handling.
- Allow partial execution and reporting for long-running batches.
- Integrates with your orchestration layer that may schedule sub-operations on workers.

Deliverable: outline a `Operation` composite API and how orchestration code would execute and monitor composed operations.
"""

from enum import Enum
from abc import ABC, abstractmethod
import time
from typing import List, Optional
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class OperationStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class OperationResult:
    def __init__(
        self,
        status: OperationStatus = OperationStatus.PENDING,
        errors: List[Exception] = None,
    ):
        self.status = status
        self.errors = errors if errors is not None else []

    @property
    def is_complete(self) -> bool:
        return self.status in {OperationStatus.SUCCESS, OperationStatus.FAILURE}

    @property
    def is_pending(self) -> bool:
        return self.status == OperationStatus.PENDING


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


class LeafOperation(Operation):
    def __init__(self, name: str, payload: dict, fail: bool = False):
        self.name = name
        self.payload = payload
        self.fail = fail
        self.result = OperationResult()
        self.id = id(self)

    def execute(self) -> OperationResult:
        try:

            self.result.status = OperationStatus.IN_PROGRESS
            time.sleep(0.5)  # simulate network latency
            if self.fail:
                print(
                    f"Executing leaf operation: {self.name} with payload: {self.payload} - Simulating failure"
                )
                raise Exception(f"Operation {self.name} failed due to simulated error.")
            else:
                self.result.status = OperationStatus.SUCCESS
            print(f"Executed leaf operation: {self.name} with payload: {self.payload}")
            return self.result
        except Exception as e:
            self.result.status = OperationStatus.FAILURE
            self.result.errors.append(e)
            return self.result

    def cancel(self) -> None:
        if self.result.status == OperationStatus.IN_PROGRESS:
            print(f"Cancelling leaf operation: {self.name}")
            self.result.status = OperationStatus.FAILURE

    def get_status(self) -> OperationStatus:
        return self.result.status


class CompositeOperation(Operation):
    def __init__(
        self,
        name: str,
        children: Optional[List[Operation]] = None,
        use_parallel: bool = False,
    ):
        self.name = name
        self.children: List[Operation] = children if children is not None else []
        self.result = OperationResult()
        self.use_parallel = use_parallel

    def add_operation(self, operation: Operation) -> None:
        self.children.append(operation)

    def _execute_parallel(self) -> OperationResult:
        start_time = time.time()
        self.result.status = OperationStatus.IN_PROGRESS
        all_success = True
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(child.execute): child for child in self.children}
            for future in as_completed(futures):
                child_result = future.result()
                if child_result.status == OperationStatus.FAILURE:
                    all_success = False
                    self.result.errors.extend(child_result.errors)
        self.result.status = (
            OperationStatus.SUCCESS if all_success else OperationStatus.FAILURE
        )
        end_time = time.time()
        print(
            f"Executed composite operation: {self.name} in {end_time - start_time:.2f} seconds"
        )
        return self.result

    def _execute_sequential(self) -> OperationResult:
        start_time = time.time()
        self.result.status = OperationStatus.IN_PROGRESS
        all_success = True
        for child in self.children:
            child_result = child.execute()
            if child_result.status == OperationStatus.FAILURE:
                all_success = False
                self.result.errors.extend(child_result.errors)
        self.result.status = (
            OperationStatus.SUCCESS if all_success else OperationStatus.FAILURE
        )
        end_time = time.time()
        print(
            f"Executed composite operation: {self.name} in {end_time - start_time:.2f} seconds"
        )
        return self.result

    def execute(self):
        if self.use_parallel:
            return self._execute_parallel()
        else:
            return self._execute_sequential()

    def cancel(self) -> None:
        print(f"Cancelling composite operation: {self.name}")
        for child in self.children:
            child.cancel()
        self.result.status = OperationStatus.FAILURE

    def get_status(self) -> OperationStatus:
        if all(
            child.get_status() == OperationStatus.SUCCESS for child in self.children
        ):
            return OperationStatus.SUCCESS
        elif any(
            child.get_status() == OperationStatus.FAILURE for child in self.children
        ):
            return OperationStatus.FAILURE
        elif any(
            child.get_status() == OperationStatus.IN_PROGRESS for child in self.children
        ):
            return OperationStatus.IN_PROGRESS
        else:
            return OperationStatus.PENDING

    def get_progress(self) -> float:
        total = len(self.children)
        if total == 0:
            return 100.0
        completed = sum(1 for child in self.children if child.result.is_complete)
        return (completed / total) * 100.0


bulk_update = CompositeOperation(
    name="bulk-update",
    children=[
        LeafOperation("user-service", {"user_id": 1}),
        LeafOperation("inventory-service", {"sku": "A1"}, fail=True),
        LeafOperation("billing-service", {"invoice": 123}),
    ],
    use_parallel=True,
)

bulk_update.execute()
print(f"Bulk update status: {bulk_update.get_status().value}")
print(f"Bulk update progress: {bulk_update.get_progress()}%")
print(f"Bulk update errors: {bulk_update.result.errors}")
