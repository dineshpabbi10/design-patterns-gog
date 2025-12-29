# Template Method Design Pattern

## Problem
In many applications, especially those involving data processing like ETL (Extract, Transform, Load) jobs, there's a common high-level algorithm that remains consistent, but the specific implementation details of individual steps vary depending on the context or data source. For example, an ETL process might always involve extracting data, transforming it, and then loading it. However, the extraction method for a CSV file will differ from that of a database, and similarly for transformation and loading.

The challenge is to define a skeleton of an algorithm in an operation, deferring some steps to subclasses. This allows subclasses to redefine certain steps of an algorithm without changing the algorithm's structure.

## Solution
The Template Method design pattern addresses this by defining the skeleton of an algorithm in a base class, but allows subclasses to override specific steps without changing the overall structure. This promotes code reuse and ensures consistency in the high-level algorithm.

In the provided Python example, `ETLTemplate` serves as the abstract base class that defines the template method `run()`. This method orchestrates the execution of the ETL process: `extract()`, `transform()`, `load()`, `validate()`, and `monitor()`. The `extract()`, `transform()`, and `load()` methods are declared as abstract, forcing subclasses to provide their concrete implementations. The `validate()` and `monitor()` methods provide default implementations that can also be overridden by subclasses if needed.

This pattern ensures that:
- The overall flow of the ETL job (extract -> transform -> load -> validate -> monitor) is fixed.
- Subclasses can provide their specific logic for extraction, transformation, and loading.
- Common pre/post steps like validation and monitoring are enforced.

## Structure
```
+----------------+       +-------------------+
| ETLTemplate    |       | ConcreteETL       |
+----------------+       +-------------------+
| + run()        |──────>| + run()           |
| + extract()    |<───── | + extract()       |
| + transform()  |<───── | + transform()     |
| + load()       |<───── | + load()          |
| + validate()   |       | + validate() (opt)|
| + monitor()    |       | + monitor() (opt) |
+----------------+       +-------------------+
```

## Example Code

```python
from abc import ABC, abstractmethod

class ETLTemplate(ABC):
    def run(self):
        self.extract()
        self.transform()
        self.load()
        self.validate()
        self.monitor()

    @abstractmethod
    def extract(self):
        pass

    @abstractmethod
    def transform(self):
        pass

    @abstractmethod
    def load(self):
        pass

    def validate(self):
        print("Validating data...")

    def monitor(self):
        print("Monitoring ETL job...")

class CSVETL(ETLTemplate):
    def extract(self):
        print("Extracting data from CSV file...")

    def transform(self):
        print("Transforming CSV data...")

    def load(self):
        print("Loading data into the database...")

# Example usage
if __name__ == "__main__":
    etl_job = CSVETL()
    etl_job.run()
```

## Unit Tests

```python
import pytest

def test_csv_etl(capsys):
    etl_job = CSVETL()
    etl_job.run()
    captured = capsys.readouterr()
    assert "Extracting data from CSV file..." in captured.out
    assert "Transforming CSV data..." in captured.out
    assert "Loading data into the database..." in captured.out
    assert "Validating data..." in captured.out
    assert "Monitoring ETL job..." in captured.out
```

## Explanation
- **`ETLTemplate` (Abstract Base Class):** This class defines the template method `run()` which outlines the fixed sequence of operations. It declares abstract methods (`extract`, `transform`, `load`) that must be implemented by concrete subclasses, and provides concrete methods (`validate`, `monitor`) with default behaviors that can be optionally overridden.
- **`CSVETL` (Concrete Class):** This class is a concrete implementation of `ETLTemplate`. It provides specific logic for `extracting` data from a CSV file, `transforming` that data, and `loading` it into a database. It reuses the default `validate` and `monitor` steps defined in the base class.

This pattern is highly effective for building frameworks where invariant parts of an algorithm are encapsulated, and variant parts are left for implementers to define.
