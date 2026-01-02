# Command Pattern

## Problem

You need to encapsulate complex operations (e.g., "create customer across services", "provision resources") as commands that can be queued, retried, logged, and undone when possible. Design a `Command` object model that supports asynchronous execution and persistent queuing.

Constraints & hints:
- Commands should be serializable to store in a durable queue.
- Support undo/compensating commands for failure recovery.
- Useful for implementing background workers and sagas across microservices.

Deliverable: specify the command interface and how commands are scheduled and retried in your system.

## Solution

Define an abstract `Command` class with `execute`, `undo`, `serialize`, and `deserialize` methods. Implement concrete commands for specific operations. Create a `CommandFactory` for deserialization and a `CommandScheduler` to manage command queuing and execution with automatic compensation on failure.

```python
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, ClassVar, Dict
import asyncio


class CommandTypes(str, Enum):
    """Enumeration of supported command types."""
    CREATE_CUSTOMER = "create_customer"
    PROVISION_RESOURCES = "provision_resources"


class Command(ABC):
    """Abstract base class for commands that can be executed, undone, and serialized.
    
    Commands encapsulate operations that can be queued, logged, retried, and rolled back.
    They support serialization for durable storage and deserialization for recovery.
    """

    @abstractmethod
    async def execute(self) -> None:
        """Execute the command."""
        pass

    @abstractmethod
    async def undo(self) -> None:
        """Undo the command if possible."""
        pass

    @abstractmethod
    async def serialize(self) -> Dict[str, Any]:
        """Serialize the command to a dictionary for storage."""
        pass

    @classmethod
    @abstractmethod
    async def deserialize(cls, data: Dict[str, Any]) -> "Command":
        """Deserialize a command from a dictionary."""
        pass


class CreateCustomerCommand(Command):
    """Command to create a new customer."""

    def __init__(self, customer_id: str, customer_data: Dict[str, Any]) -> None:
        """Initialize the create customer command."""
        self.customer_id = customer_id
        self.customer_data = customer_data

    async def execute(self) -> None:
        """Create the customer."""
        print(f"Creating customer {self.customer_id} with data {self.customer_data}")

    async def undo(self) -> None:
        """Delete the created customer (compensation)."""
        print(f"Deleting customer {self.customer_id}")

    async def serialize(self) -> Dict[str, Any]:
        """Serialize the command for storage."""
        return {
            "type": CommandTypes.CREATE_CUSTOMER,
            "customer_id": self.customer_id,
            "customer_data": self.customer_data,
        }

    @classmethod
    async def deserialize(cls, data: Dict[str, Any]) -> "CreateCustomerCommand":
        """Deserialize from dictionary."""
        return cls(customer_id=data["customer_id"], customer_data=data["customer_data"])


class ProvisionResourcesCommand(Command):
    """Command to provision cloud resources."""

    def __init__(self, resource_id: str, resource_config: Dict[str, Any]) -> None:
        """Initialize the provision resources command."""
        self.resource_id = resource_id
        self.resource_config = resource_config

    async def execute(self) -> None:
        """Provision the resources."""
        print(f"Provisioning resources {self.resource_id} with config {self.resource_config}")

    async def undo(self) -> None:
        """Deprovision the resources (compensation)."""
        print(f"Deprovisioning resources {self.resource_id}")

    async def serialize(self) -> Dict[str, Any]:
        """Serialize the command for storage."""
        return {
            "type": CommandTypes.PROVISION_RESOURCES,
            "resource_id": self.resource_id,
            "resource_config": self.resource_config,
        }

    @classmethod
    async def deserialize(cls, data: Dict[str, Any]) -> "ProvisionResourcesCommand":
        """Deserialize from dictionary."""
        return cls(
            resource_id=data["resource_id"], resource_config=data["resource_config"]
        )


class CommandFactory:
    """Factory to create command instances from serialized data."""

    command_map: ClassVar[Dict[CommandTypes, type[Command]]] = {
        CommandTypes.CREATE_CUSTOMER: CreateCustomerCommand,
        CommandTypes.PROVISION_RESOURCES: ProvisionResourcesCommand,
    }

    @classmethod
    async def create_command(cls, data: Dict[str, Any]) -> Command:
        """Create a command instance from serialized data."""
        command_type = data.get("type")
        command_class = cls.command_map.get(command_type)
        if not command_class:
            raise ValueError(f"Unknown command type: {command_type}")
        return await command_class.deserialize(data)


class CommandScheduler:
    """Schedules and executes commands from a queue."""

    def __init__(self) -> None:
        """Initialize the command scheduler with an empty queue."""
        self.queue: list[Dict[str, Any]] = []

    async def schedule(self, command: Command) -> None:
        """Schedule a command for execution."""
        serialized_command = await command.serialize()
        self.queue.append(serialized_command)
        print(f"Scheduled command: {serialized_command}")

    async def execute_next(self) -> None:
        """Execute the next command in the queue."""
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
```

## Key Features

- **Encapsulation**: Operations are wrapped as command objects, making them first-class values.
- **Serialization**: Commands can be persisted to a durable queue for recovery.
- **Asynchronous Execution**: Built on async/await for non-blocking execution.
- **Automatic Compensation**: Failed commands trigger undo operations in reverse order.
- **Factory Pattern**: Dynamic command creation from serialized data.
- **Extensibility**: New commands can be added by implementing the Command interface.

## Usage in Your Code

```python
async def main() -> None:
    """Demonstrate command execution using the CommandScheduler."""
    scheduler = CommandScheduler()
    
    # Schedule customer creation
    command = CreateCustomerCommand(
        customer_id="123", customer_data={"name": "John Doe"}
    )
    await scheduler.schedule(command)
    await scheduler.execute_next()
    
    # Schedule resource provisioning
    command2 = ProvisionResourcesCommand(
        resource_id="res-456", resource_config={"type": "vm", "size": "large"}
    )
    await scheduler.schedule(command2)
    await scheduler.execute_next()


if __name__ == "__main__":
    asyncio.run(main())
```

## Advantages & Disadvantages

| Pros | Cons |
|------|------|
| Encapsulates operations as objects | Adds complexity for simple operations |
| Supports undo/compensation patterns | Requires careful design of undo logic |
| Enables queuing and retries | Async operations can be hard to debug |
| Serializable for durability | Potential memory overhead if many commands queued |
| Decouples requestor from executor | Need to manage command ordering |
| Supports logging and auditing | Factory can become large with many commands |

## Testing Tip

Mock the underlying services to test command behavior without side effects:

```python
from unittest.mock import AsyncMock, Mock

async def test_command_execution():
    """Test command execution without side effects."""
    # Test successful execution
    command = CreateCustomerCommand(
        customer_id="test123", customer_data={"name": "Test User"}
    )
    await command.execute()
    await command.undo()
    
    # Test serialization round-trip
    serialized = await command.serialize()
    deserialized = await CreateCustomerCommand.deserialize(serialized)
    assert command.customer_id == deserialized.customer_id
    assert command.customer_data == deserialized.customer_data
```

## Real-World Applications

- **Microservices Sagas**: Orchestrate multi-service transactions with compensation.
- **Background Jobs**: Queue long-running operations for asynchronous processing.
- **Audit Logging**: Track all operations in a durable, auditable queue.
- **Distributed Transactions**: Implement two-phase commit patterns.
- **Event Sourcing**: Store commands as events for complete history.
