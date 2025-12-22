"""
Problem: Your application uses a complex onboarding subsystem that interacts with identity, billing, and a third-party
provider (ParagoN). Create a `Facade` that offers a single high-level API for onboarding a user, hiding the orchestration
and error-recovery details from callers (frontend and other services).

Constraints & hints:
- Facade should orchestrate multiple internal calls and present a simple success/failure result.
- Useful to keep controllers and frontends simple.
- Consider idempotency for retries.

Deliverable: define the facade interface and an example flow for `onboard_user()`.
"""

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass(frozen=True)
class OnboardUserRequest:
    user_id: str
    email: str
    plan_id: str
    idempotency_key: str


@dataclass
class OnboardUserResult:
    success: bool
    user_id: Optional[str] = None
    error: Optional[str] = None


class IdentityService:
    def create_user(self, user_id: str, email: str) -> None:
        print(f"[Identity] Creating user {user_id} ({email})")


class BillingService:
    def create_subscription(self, user_id: str, plan_id: str) -> None:
        print(f"[Billing] Creating subscription for {user_id} on plan {plan_id}")

    def cancel_subscription(self, user_id: str) -> None:
        print(f"[Billing] Cancelling subscription for {user_id}")


class ParagoNClient:
    def provision_account(self, user_id: str) -> None:
        print(f"[ParagoN] Provisioning account for {user_id}")

    def deprovision_account(self, user_id: str) -> None:
        print(f"[ParagoN] Deprovisioning account for {user_id}")


class IdempotencyStore:
    def __init__(self):
        self._store: Dict[str, OnboardUserResult] = {}

    def get(self, key: str) -> Optional[OnboardUserResult]:
        return self._store.get(key)

    def save(self, key: str, result: OnboardUserResult) -> None:
        self._store[key] = result


# Facade class
class OnboardingFacade:
    """
    Facade that hides onboarding orchestration, retries, and recovery
    behind a single high-level API.
    """

    def __init__(
        self,
        identity: IdentityService,
        billing: BillingService,
        paragon: ParagoNClient,
        idempotency_store: IdempotencyStore,
    ):
        self.identity = identity
        self.billing = billing
        self.paragon = paragon
        self.idempotency_store = idempotency_store

    def onboard_user(self, request: OnboardUserRequest) -> OnboardUserResult:
        # 1. Idempotency check
        cached = self.idempotency_store.get(request.idempotency_key)
        if cached:
            print("[Facade] Returning cached result")
            return cached

        try:
            # 2. Orchestration
            self.identity.create_user(request.user_id, request.email)
            self.billing.create_subscription(request.user_id, request.plan_id)
            self.paragon.provision_account(request.user_id)

            result = OnboardUserResult(
                success=True,
                user_id=request.user_id,
            )

        except Exception as e:
            # 3. Error handling + compensation
            self._rollback(request)
            result = OnboardUserResult(
                success=False,
                error=str(e),
            )

        # 4. Save result for idempotent retries
        self.idempotency_store.save(request.idempotency_key, result)
        return result

    def _rollback(self, request: OnboardUserRequest) -> None:
        print("[Facade] Rolling back onboarding")

        # Best-effort compensation (no exceptions escape)
        try:
            self.paragon.deprovision_account(request.user_id)
        except Exception:
            pass

        try:
            self.billing.cancel_subscription(request.user_id)
        except Exception:
            pass


if __name__ == "__main__":
    facade = OnboardingFacade(
        identity=IdentityService(),
        billing=BillingService(),
        paragon=ParagoNClient(),
        idempotency_store=IdempotencyStore(),
    )

    request = OnboardUserRequest(
        user_id="user-123",
        email="user@example.com",
        plan_id="pro",
        idempotency_key="req-001",
    )

    result = facade.onboard_user(request)
    print("Result:", result)

    # Retry (idempotent)
    result = facade.onboard_user(request)
    print("Result:", result)
