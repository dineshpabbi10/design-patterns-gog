"""
Problem: Third-party APIs return paginated results. Build an `Iterator` abstraction that yields domain objects across
pages transparently and integrates with your async and sync callers (both backend and ingestion workers).

Constraints & hints:
- Support backpressure for streaming consumers.
- Provide adapters for both sync and async iteration.
- Handle rate limits and transient errors while paginating.

Deliverable: define an iterator interface and examples for iterating over a paginated ParagoN endpoint.
"""


class SyncCaller:
    def fetch_page(self, page_token=None):
        # Simulate fetching a page of results from a paginated API
        if page_token is None:
            return {"data": [1, 2, 3], "next_page_token": "token1"}
        elif page_token == "token1":
            return {"data": [4, 5, 6], "next_page_token": "token2"}
        elif page_token == "token2":
            return {"data": [7, 8, 9], "next_page_token": None}
        else:
            return {"data": [], "next_page_token": None}


class AsyncCaller:
    async def fetch_page(self, page_token=None):
        # Simulate fetching a page of results from a paginated API
        if page_token is None:
            return {"data": [1, 2, 3], "next_page_token": "token1"}
        elif page_token == "token1":
            return {"data": [4, 5, 6], "next_page_token": "token2"}
        elif page_token == "token2":
            return {"data": [7, 8, 9], "next_page_token": None}
        else:
            return {"data": [], "next_page_token": None}


class PaginatedIterator:
    def __init__(self, caller: SyncCaller):
        self.caller = caller
        self.page_token = None
        self.buffer = []
        self.finished = False

    def __iter__(self):
        return self

    def __next__(self):
        if not self.buffer and not self.finished:
            page = self.caller.fetch_page(self.page_token)
            self.buffer.extend(page["data"])
            self.page_token = page["next_page_token"]
            if self.page_token is None:
                self.finished = True
        if not self.buffer:
            raise StopIteration
        return self.buffer.pop(0)


class AsyncPaginatedIterator:
    def __init__(self, caller: AsyncCaller):
        self.caller = caller
        self.page_token = None
        self.buffer = []
        self.finished = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self.buffer and not self.finished:
            page = await self.caller.fetch_page(self.page_token)
            self.buffer.extend(page["data"])
            self.page_token = page["next_page_token"]
            if self.page_token is None:
                self.finished = True
        if not self.buffer:
            raise StopAsyncIteration
        return self.buffer.pop(0)


# Example usage for sync iterator
sync_caller = SyncCaller()
sync_iterator = PaginatedIterator(sync_caller)
for item in sync_iterator:
    print(f"Sync item: {item}")

# Example usage for async iterator
import asyncio


async def async_main():
    async_caller = AsyncCaller()
    async_iterator = AsyncPaginatedIterator(async_caller)
    async for item in async_iterator:
        print(f"Async item: {item}")


asyncio.run(async_main())

# Unit tests with pytest
import pytest


def test_sync_iterator():
    sync_caller = SyncCaller()
    sync_iterator = PaginatedIterator(sync_caller)
    results = list(sync_iterator)
    assert results == [1, 2, 3, 4, 5, 6, 7, 8, 9]


@pytest.mark.asyncio
async def test_async_iterator():
    async_caller = AsyncCaller()
    async_iterator = AsyncPaginatedIterator(async_caller)
    results = []
    async for item in async_iterator:
        results.append(item)
    assert results == [1, 2, 3, 4, 5, 6, 7, 8, 9]
