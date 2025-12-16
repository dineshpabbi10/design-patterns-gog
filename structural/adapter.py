"""
Problem: Your microservices and React frontend rely on consistent internal data models (DTOs) for users, orders, and other entities.
However, the ParagoN API (which you interact with via your custom ParagoNClient) returns deeply nested JSON responses with inconsistent
field naming conventions, optional fields, and different data types than your internal models expect. For example:

- ParagoN API response for a user:
  {
    "user_id": "12345",
    "personal_info": {
      "firstName": "John",
      "lastName": "Doe",
      "contact": {
        "email_addr": "john.doe@example.com",
        "phone_num": "+1234567890"
      }
    },
    "account_status": "ACTIVE",
    "created_at": "2023-10-01T12:00:00Z",
    "metadata": {
      "tags": ["premium", "verified"],
      "preferences": {"notifications": true}
    }
  }

- Your internal User model (used by React components and backend services):
  {
    "id": "12345",
    "firstName": "John",
    "lastName": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1234567890",
    "status": "active",
    "createdAt": "2023-10-01T12:00:00Z",
    "tags": ["premium", "verified"],
    "preferences": {"notifications": true}
  }

The discrepancies include:
- Field name variations (user_id vs id, firstName vs firstName, email_addr vs email, account_status vs status)
- Nested structures flattened or restructured
- Type conversions (string status to lowercase)
- Optional fields that may be missing
- Additional fields that should be ignored or transformed

Create an Adapter pattern implementation that:
1. Converts ParagoN API responses to your internal User model
2. Converts internal User models back to ParagoN API format for requests/updates
3. Handles bidirectional mapping safely

Constraints & hints:
- The adapter should hide third-party quirks (field names, missing fields, type differences) so your codebase remains stable when ParagoN changes their API.
- Make adapters composable for layered transformations (e.g., combine field mapping + type conversion + validation).
- Consider performance for high-throughput API calls (e.g., avoid deep copying unless necessary, use efficient data structures).
- Support partial updates and error handling for malformed responses.
- Allow adapters to be easily extended or swapped for different API versions.

Deliverable: 
- Define an abstract Adapter interface with methods for to_internal() and to_external().
- Implement a concrete ParagoNUserAdapter class that maps ParagoN API responses to your internal User model and vice versa.
- Include unit tests demonstrating the adapter's functionality, including edge cases like missing fields and type conversions.
"""
from abc import ABC, abstractmethod

class BaseAdapterModel(ABC):
    def __init__(self,external_data: dict):
        self.external_data = external_data

    @abstractmethod
    def to_internal(self) -> dict:
        raise NotImplementedError("to_internal method not implemented")
    
    @abstractmethod
    def to_external(self) -> dict:
        raise NotImplementedError("to_external method not implemented")


class ParagoNUserAdapter(BaseAdapterModel):
    def to_internal(self) -> dict:
        data = self.external_data
        internal_data = {
            "id": data.get("user_id"),
            "firstName": data.get("personal_info", {}).get("firstName"),
            "lastName": data.get("personal_info", {}).get("lastName"),
            "email": data.get("personal_info", {}).get("contact", {}).get("email_addr"),
            "phone": data.get("personal_info", {}).get("contact", {}).get("phone_num"),
            "status": data.get("account_status", "").lower(),
            "createdAt": data.get("created_at"),
            "tags": data.get("metadata", {}).get("tags", []),
            "preferences": data.get("metadata", {}).get("preferences", {}),
        }
        return internal_data

    def to_external(self) -> dict:
        internal_data = self.external_data
        external_data = {
            "user_id": internal_data.get("id"),
            "personal_info": {
                "firstName": internal_data.get("firstName"),
                "lastName": internal_data.get("lastName"),
                "contact": {
                    "email_addr": internal_data.get("email"),
                    "phone_num": internal_data.get("phone"),
                },
            },
            "account_status": internal_data.get("status", "").upper(),
            "created_at": internal_data.get("createdAt"),
            "metadata": {
                "tags": internal_data.get("tags", []),
                "preferences": internal_data.get("preferences", {}),
            },
        }
        return external_data
    

import pytest 
import copy

@pytest.fixture
def paragon_user_data():
    return {
        "user_id": "12345",
        "personal_info": {
            "firstName": "John",
            "lastName": "Doe",
            "contact": {
                "email_addr": "<EMAIL>",
                "phone_num": "555-1234",
            },
        },
        "account_status": "ACTIVE",
        "created_at": "2023-01-01T00:00:00Z",
        "metadata": {
            "tags": ["premium", "vip"],
            "preferences": {"notifications": True},
        },
    }

@pytest.fixture
def expected_user_data():
    return {
        "id": "12345",
        "firstName": "John",
        "lastName": "Doe",
        "email": "<EMAIL>",
        "phone": "555-1234",
        "status": "active",
        "createdAt": "2023-01-01T00:00:00Z",
        "tags": ["premium", "vip"],
        "preferences": {"notifications": True},
    }

class TestParagoNUserAdapter:
    def test_to_internal_complete_data(self,paragon_user_data,expected_user_data):
        external_data = paragon_user_data
        adapter = ParagoNUserAdapter(external_data)
        result = adapter.to_internal()
        assert result == expected_user_data
                
    def test_to_external_complete_data(self,paragon_user_data,expected_user_data):
        internal_data = expected_user_data
        adapter = ParagoNUserAdapter(internal_data)
        result = adapter.to_external()
        assert result == paragon_user_data

    def test_to_internal_missing_optional_fields(self, paragon_user_data, expected_user_data):
        external_data = copy.deepcopy(paragon_user_data)
        del external_data["metadata"]["tags"]
        adapter = ParagoNUserAdapter(external_data)
        result = adapter.to_internal()
        expected_data = copy.deepcopy(expected_user_data)
        expected_data["tags"] = []
        assert result == expected_data

    
