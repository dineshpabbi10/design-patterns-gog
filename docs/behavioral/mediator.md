# Mediator Pattern

## Problem

Several modules (auth, billing, notifications, UI updates) need coordinated interactions during user lifecycle operations. Design a `Mediator` that centralizes interaction logic so modules don't reference each other directly.

Constraints & hints:
- Mediator should manage sequencing, retries, and error propagation between participants.
- Useful for reducing coupling between microservices or in-process modules.
- Consider pluggable participants and observability hooks.

Deliverable: define the mediator contract and an example scenario for user profile synchronization.

## Solution

Define an abstract `MediatorStep` class with `execute` and `compensate` methods. Implement concrete steps that wrap individual services. Create a `UserLifecycleMediator` that orchestrates the steps with built-in retry logic and transactional compensation (rollback) on failure.

```python
from abc import ABC, abstractmethod
import random


class BillingService:
    """Service responsible for charging users."""

    def charge_user(self, user_id: int, amount: float) -> None:
        """Charge a user the specified amount."""
        if random.choice([True, False]):
            raise Exception("Billing service failed.")
        print(f"Charging user {user_id} an amount of {amount}.")


class AuthService:
    """Service responsible for user authentication."""

    def authenticate_user(self, user_id: int) -> None:
        """Authenticate a user."""
        if random.choice([True, False]):
            raise Exception("Authentication service failed.")
        print(f"Authenticating user {user_id}.")


class NotificationService:
    """Service responsible for sending notifications to users."""

    def send_notification(self, user_id: int, message: str) -> None:
        """Send a notification to a user."""
        if random.choice([True, False]):
            raise Exception("Notification service failed.")
        print(f"Sending notification to user {user_id}: {message}")


class MediatorPayload:
    """Payload containing data for mediator step execution."""

    def __init__(self, user_id: int, amount: float, message: str) -> None:
        """Initialize the mediator payload."""
        self.user_id = user_id
        self.amount = amount
        self.message = message


class MediatorStep(ABC):
    """Abstract base class for mediator steps."""

    @abstractmethod
    def execute(self, payload: MediatorPayload) -> None:
        """Execute the step."""
        pass

    def compensate(self, payload: MediatorPayload) -> None:
        """Compensate/rollback this step if a later step fails."""
        pass


class AuthStep(MediatorStep):
    """Mediator step for user authentication."""

    def __init__(self, auth_service: AuthService) -> None:
        """Initialize the authentication step."""
        self.auth_service = auth_service

    def execute(self, payload: MediatorPayload) -> None:
        """Execute authentication."""
        self.auth_service.authenticate_user(payload.user_id)

    def compensate(self, payload: MediatorPayload) -> None:
        """Rollback authentication."""
        print(f"Compensating authentication for user {payload.user_id}.")


class BillingStep(MediatorStep):
    """Mediator step for charging users."""

    def __init__(self, billing_service: BillingService) -> None:
        """Initialize the billing step."""
        self.billing_service = billing_service

    def execute(self, payload: MediatorPayload) -> None:
        """Execute billing charge."""
        self.billing_service.charge_user(payload.user_id, payload.amount)

    def compensate(self, payload: MediatorPayload) -> None:
        """Rollback billing charge."""
        print(f"Compensating billing for user {payload.user_id}.")


class NotificationStep(MediatorStep):
    """Mediator step for sending notifications."""

    def __init__(self, notification_service: NotificationService) -> None:
        """Initialize the notification step."""
        self.notification_service = notification_service

    def execute(self, payload: MediatorPayload) -> None:
        """Execute notification send."""
        self.notification_service.send_notification(payload.user_id, payload.message)

    def compensate(self, payload: MediatorPayload) -> None:
        """Rollback notification send."""
        print(f"Compensating notification for user {payload.user_id}.")


class UserLifecycleMediator:
    """Mediator that orchestrates user lifecycle operations with retry and compensation logic."""

    def __init__(self, steps: list[MediatorStep], num_of_retry: int = 3) -> None:
        """Initialize the mediator with a sequence of steps."""
        self.steps = steps
        self.num_of_retry = num_of_retry

    def execute(self, payload: MediatorPayload) -> None:
        """Execute all steps in sequence with compensation on failure."""
        executed_steps: list[MediatorStep] = []
        try:
            for step in self.steps:
                self.execute_with_retry(step, payload)
                executed_steps.append(step)
        except Exception as e:
            print(f"Error occurred: {e}. Initiating compensation.")
            for step in reversed(executed_steps):
                step.compensate(payload)

    def execute_with_retry(self, step: MediatorStep, payload: MediatorPayload) -> None:
        """Execute a step with retry logic."""
        for attempt in range(self.num_of_retry):
            try:
                step.execute(payload)
                return
            except Exception as e:
                print(f"Retry {attempt + 1} failed: {e}")
                if attempt == self.num_of_retry - 1:
                    print("Max retries reached. Raising exception.")
                    raise e
```

## Key Features

- **Centralized Orchestration**: All module interactions flow through the mediator, reducing coupling.
- **Retry Logic**: Automatic retry mechanism built-in for fault tolerance.
- **Compensation/Rollback**: Failed operations trigger automatic compensation in reverse order.
- **Pluggable Steps**: New steps can be added without modifying the mediator logic.
- **Observability**: Clear logging of execution, retries, and compensation.

## Usage in Your Code

```python
# Example usage
if __name__ == "__main__":
    auth_service = AuthService()
    billing_service = BillingService()
    notification_service = NotificationService()

    steps = [
        AuthStep(auth_service),
        BillingStep(billing_service),
        NotificationStep(notification_service),
    ]

    mediator = UserLifecycleMediator(steps)

    payload = MediatorPayload(user_id=1, amount=100, message="Welcome to our service!")
    mediator.execute(payload)
```

## Advantages & Disadvantages

| Pros | Cons |
|------|------|
| Reduces coupling between modules | Mediator can become a bottleneck or "God Object" |
| Centralizes complex orchestration logic | Harder to trace execution flow across steps |
| Built-in retry and compensation patterns | Requires careful design of step ordering |
| Easy to add new steps | Testing mediator logic can be complex |
| Improves maintainability of interactions | May add latency for sequential operations |

## Testing Tip

Mock the services and steps in unit tests to verify mediator behavior without real side effects.

```python
from unittest.mock import Mock

# Mock services
mock_auth = Mock()
mock_billing = Mock()
mock_notification = Mock()

auth_step = AuthStep(mock_auth)
billing_step = BillingStep(mock_billing)
notification_step = NotificationStep(mock_notification)

mediator = UserLifecycleMediator([auth_step, billing_step, notification_step])

# Test payload
payload = MediatorPayload(user_id=1, amount=100, message="Test")

# Execute and verify calls
mediator.execute(payload)
mock_auth.authenticate_user.assert_called_once_with(1)
mock_billing.charge_user.assert_called_once_with(1, 100)
mock_notification.send_notification.assert_called_once_with(1, "Test")
```
