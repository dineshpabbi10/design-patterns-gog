"""
Problem: You need to encapsulate complex operations (e.g., "create customer across services", "provision resources") as
commands that can be queued, retried, logged, and undone when possible. Design a `Command` object model that supports
asynchronous execution and persistent queuing.

Constraints & hints:
- Commands should be serializable to store in a durable queue.
- Support undo/compensating commands for failure recovery.
- Useful for implementing background workers and sagas across microservices.

Deliverable: specify the command interface and how commands are scheduled and retried in your system.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, ClassVar, Dict
import random
import os
import asyncio
import pytest


def simulate_failure() -> None:
    """Simulate a command failure based on FAILURE_RATE environment variable.

    The FAILURE_RATE environment variable controls the probability of failure.
    Default is 0.3 (30% chance to fail).

    Raises:
        Exception: If random selection triggers failure.
    """
    failure_rate = float(os.getenv("FAILURE_RATE", 0.3))
    if random.random() < failure_rate:
        raise Exception("Simulated command failure")


class CommandTypes(str, Enum):
    CREATE_CUSTOMER = "create_customer"
    PROVISION_RESOURCES = "provision_resources"


class Command(ABC):
    """Abstract base class for commands that can be executed, undone, and serialized.

    Commands encapsulate operations that can be queued, logged, retried, and rolled back.
    They support serialization for durable storage and deserialization for recovery.
    """

    @abstractmethod
    async def execute(self) -> None:
        """Execute the command.

        Raises:
            Exception: If command execution fails.
        """
        pass

    @abstractmethod
    async def undo(self) -> None:
        """Undo the command if possible.

        This method should reverse the effects of execute() for failure recovery.

        Raises:
            Exception: If undo operation fails.
        """
        pass

    @abstractmethod
    async def serialize(self) -> Dict[str, Any]:
        """Serialize the command to a dictionary for storage.

        Returns:
            Dictionary containing command type and all necessary data for reconstruction.
        """
        pass

    @classmethod
    @abstractmethod
    async def deserialize(cls, data: Dict[str, Any]) -> "Command":
        """Deserialize a command from a dictionary.

        Args:
            data: Dictionary containing command type and data.

        Returns:
            Reconstructed Command instance.
        """
        pass

    def __str__(self) -> str:
        """Return a string representation of the command.

        Returns:
            String describing the command class.
        """
        return f"{self.__class__.__name__}()"


class CreateCustomerCommand(Command):
    """Command to create a new customer.

    This command encapsulates the logic for creating a customer across services.
    """

    def __init__(self, customer_id: str, customer_data: Dict[str, Any]) -> None:
        """Initialize the create customer command.

        Args:
            customer_id: Unique identifier for the customer.
            customer_data: Dictionary containing customer information.
        """
        self.customer_id = customer_id
        self.customer_data = customer_data

    async def execute(self) -> None:
        """Create the customer.

        Raises:
            Exception: If customer creation fails.
        """
        simulate_failure()
        print(f"Creating customer {self.customer_id} with data {self.customer_data}")

    async def undo(self) -> None:
        """Delete the created customer (compensation)."""
        print(f"Deleting customer {self.customer_id}")

    async def serialize(self) -> Dict[str, Any]:
        """Serialize the command for storage.

        Returns:
            Dictionary with command type and customer data.
        """
        return {
            "type": CommandTypes.CREATE_CUSTOMER,
            "customer_id": self.customer_id,
            "customer_data": self.customer_data,
        }

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            String describing the command and customer ID.
        """
        return f"CreateCustomerCommand(customer_id={self.customer_id})"

    @classmethod
    async def deserialize(cls, data: Dict[str, Any]) -> "CreateCustomerCommand":
        """Deserialize from dictionary.

        Args:
            data: Dictionary containing customer_id and customer_data.

        Returns:
            CreateCustomerCommand instance.
        """
        return cls(customer_id=data["customer_id"], customer_data=data["customer_data"])


class ProvisionResourcesCommand(Command):
    """Command to provision cloud resources.

    This command encapsulates the logic for provisioning resources with specific configuration.
    """

    def __init__(self, resource_id: str, resource_config: Dict[str, Any]) -> None:
        """Initialize the provision resources command.

        Args:
            resource_id: Unique identifier for the resource.
            resource_config: Dictionary containing resource configuration.
        """
        self.resource_id = resource_id
        self.resource_config = resource_config

    async def execute(self) -> None:
        """Provision the resources.

        Raises:
            Exception: If resource provisioning fails.
        """
        simulate_failure()
        print(
            f"Provisioning resources {self.resource_id} with config {self.resource_config}"
        )

    async def undo(self) -> None:
        """Deprovision the resources (compensation)."""
        print(f"Deprovisioning resources {self.resource_id}")

    async def serialize(self) -> Dict[str, Any]:
        """Serialize the command for storage.

        Returns:
            Dictionary with command type and resource data.
        """
        return {
            "type": CommandTypes.PROVISION_RESOURCES,
            "resource_id": self.resource_id,
            "resource_config": self.resource_config,
        }

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            String describing the command and resource ID.
        """
        return f"ProvisionResourcesCommand(resource_id={self.resource_id})"

    @classmethod
    async def deserialize(cls, data: Dict[str, Any]) -> "ProvisionResourcesCommand":
        """Deserialize from dictionary.

        Args:
            data: Dictionary containing resource_id and resource_config.

        Returns:
            ProvisionResourcesCommand instance.
        """
        return cls(
            resource_id=data["resource_id"], resource_config=data["resource_config"]
        )


class CommandFactory:
    """Factory to create command instances from serialized data.

    Maintains a registry of command types and their corresponding classes.
    Handles deserialization of commands from dictionaries.
    """

    command_map: ClassVar[Dict[CommandTypes, type[Command]]] = {
        CommandTypes.CREATE_CUSTOMER: CreateCustomerCommand,
        CommandTypes.PROVISION_RESOURCES: ProvisionResourcesCommand,
    }

    @classmethod
    async def create_command(cls, data: Dict[str, Any]) -> Command:
        """Create a command instance from serialized data.

        Args:
            data: Dictionary containing 'type' and command-specific fields.

        Returns:
            Deserialized Command instance.

        Raises:
            ValueError: If the command type is not registered.
        """
        command_type = data.get("type")
        command_class = cls.command_map.get(command_type)
        if not command_class:
            raise ValueError(f"Unknown command type: {command_type}")
        return await command_class.deserialize(data)


class CommandScheduler:
    """Schedules and executes commands from a queue.

    Manages command serialization, storage, and execution with automatic
    undo/compensation on failure.
    """

    def __init__(self) -> None:
        """Initialize the command scheduler with an empty queue."""
        self.queue: list[Dict[str, Any]] = []

    async def schedule(self, command: Command) -> None:
        """Schedule a command for execution.

        Serializes the command and adds it to the execution queue.

        Args:
            command: The Command instance to schedule.
        """
        serialized_command = await command.serialize()
        self.queue.append(serialized_command)
        print(f"Scheduled command: {serialized_command}")

    async def execute_next(self) -> None:
        """Execute the next command in the queue.

        Dequeues and deserializes the next command, executes it, and
        automatically undoes it on failure for compensation.
        """
        if not self.queue:
            print("No commands to execute.")
            return

        serialized_command = self.queue.pop(0)
        command = await CommandFactory.create_command(serialized_command)
        try:
            await command.execute()
            print(f"Executed command: {serialized_command}")
        except Exception as e:
            print(f"Command execution failed: {e}. Attempting to undo.")
            await command.undo()
            print(f"Undid command: {serialized_command}")


async def main() -> None:
    """Demonstrate command execution using the CommandScheduler.

    Creates and schedules two commands: one for customer creation and one
    for resource provisioning. Shows how commands are serialized, queued,
    and executed.
    """
    scheduler = CommandScheduler()
    command = CreateCustomerCommand(
        customer_id="123", customer_data={"name": "John Doe"}
    )
    await scheduler.schedule(command)
    await scheduler.execute_next()
    # Another example usage:
    command2 = ProvisionResourcesCommand(
        resource_id="res-456", resource_config={"type": "vm", "size": "large"}
    )
    await scheduler.schedule(command2)
    await scheduler.execute_next()

    # Test logging
    print("Testing command execution and logging.")
    print(command)
    print(command2)


if __name__ == "__main__":
    asyncio.run(main())


@pytest.mark.asyncio
async def test_create_customer_command() -> None:
    """Test CreateCustomerCommand serialization and execution."""
    os.environ["FAILURE_RATE"] = "0.0"
    command = CreateCustomerCommand(
        customer_id="test123", customer_data={"name": "Test User"}
    )
    serialized = await command.serialize()
    deserialized_command = await CreateCustomerCommand.deserialize(serialized)
    assert command.customer_id == deserialized_command.customer_id
    assert command.customer_data == deserialized_command.customer_data
    await command.execute()
    await command.undo()


@pytest.mark.asyncio
async def test_provision_resources_command() -> None:
    """Test ProvisionResourcesCommand serialization and execution."""
    os.environ["FAILURE_RATE"] = "0.0"
    command = ProvisionResourcesCommand(
        resource_id="res-test", resource_config={"type": "db", "size": "small"}
    )
    serialized = await command.serialize()
    deserialized_command = await ProvisionResourcesCommand.deserialize(serialized)
    assert command.resource_id == deserialized_command.resource_id
    assert command.resource_config == deserialized_command.resource_config
    await command.execute()
    await command.undo()


@pytest.mark.asyncio
async def test_command_scheduler() -> None:
    """Test CommandScheduler scheduling and execution."""
    os.environ["FAILURE_RATE"] = "0.0"
    scheduler = CommandScheduler()
    command = CreateCustomerCommand(
        customer_id="sched123", customer_data={"name": "Scheduler User"}
    )
    await scheduler.schedule(command)
    assert len(scheduler.queue) == 1
    await scheduler.execute_next()
    assert len(scheduler.queue) == 0
    command2 = ProvisionResourcesCommand(
        resource_id="res-sched", resource_config={"type": "cache", "size": "medium"}
    )
    await scheduler.schedule(command2)
    assert len(scheduler.queue) == 1
    await scheduler.execute_next()
    assert len(scheduler.queue) == 0


@pytest.mark.asyncio
async def test_command_logging() -> None:
    """Test command string representation."""
    os.environ["FAILURE_RATE"] = "0.0"
    command = CreateCustomerCommand(
        customer_id="log123", customer_data={"name": "Log User"}
    )
    assert str(command) == "CreateCustomerCommand(customer_id=log123)"
    command2 = ProvisionResourcesCommand(
        resource_id="res-log", resource_config={"type": "queue", "size": "large"}
    )
    assert str(command2) == "ProvisionResourcesCommand(resource_id=res-log)"


@pytest.mark.asyncio
async def test_command_failure_and_undo() -> None:
    """Test command failure handling and automatic undo."""
    os.environ["FAILURE_RATE"] = "1.0"  # Force failure
    scheduler = CommandScheduler()
    command = CreateCustomerCommand(
        customer_id="fail123", customer_data={"name": "Fail User"}
    )
    await scheduler.schedule(command)
    await scheduler.execute_next()  # This should fail and trigger undo
