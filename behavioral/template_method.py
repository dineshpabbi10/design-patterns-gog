"""
Problem: Define a `TemplateMethod` for ETL jobs where the high-level 
algorithm is fixed (extract -> transform -> load),
but specific steps vary per dataset. Provide base skeleton 
and subclass hooks for dataset-specific behavior.

Constraints & hints:
- Template should enforce common pre/post steps like validation and monitoring.
- Allow subclasses to override transform and enrichment steps safely.
- Useful for maintaining consistent lifecycle across many pipelines.

Deliverable: sketch the base ETL template and an example subclass for a specific data 
source.
"""
from abc import ABC, abstractmethod 
class ETLTemplate:
    def run(self):
        self.extract()
        self.transform()
        self.load()
        self.validate()
        self.monitor()

    @abstractmethod
    def extract(self):
        raise NotImplementedError("Subclasses must implement extract method")
    
    @abstractmethod
    def transform(self):
        raise NotImplementedError("Subclasses must implement transform method")

    @abstractmethod
    def load(self):
        raise NotImplementedError("Subclasses must implement load method")

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

### Unit test with pytest
def test_csv_etl(capsys):
    etl_job = CSVETL()
    etl_job.run()
    captured = capsys.readouterr()
    assert "Extracting data from CSV file..." in captured.out
    assert "Transforming CSV data..." in captured.out
    assert "Loading data into the database..." in captured.out
    assert "Validating data..." in captured.out
    assert "Monitoring ETL job..." in captured.out

    