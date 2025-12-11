"""
Problem: Define a `SparkJobBuilder` that assembles complex Spark job configurations for your data pipelines. Jobs
have many optional parts: input sources, transforms, windowing, triggers, resource settings, and monitoring hooks.
Create a builder that produces an immutable job spec used by the pipeline runner.

Constraints & hints:
- Many fields are optional; builder should allow fluent chaining.
- Final spec must be serializable and versioned for reproducible runs.
- Builders help in generating similar jobs programmatically from templates.

Deliverable: implement a `SparkJobBuilder` API that callers in orchestration code can use to produce job specs.
"""


class SparkJobSpec:
    def __init__(self, input_source, transforms, windowing, triggers, resources, monitoring_hooks):
        self.input_source = input_source
        self.transforms = transforms
        self.windowing = windowing
        self.triggers = triggers
        self.resources = resources
        self.monitoring_hooks = monitoring_hooks

    def __setattr__(self, key, value):
        if hasattr(self, key):
            raise AttributeError("Cannot modify immutable SparkJobSpec")
        super().__setattr__(key, value)

    def serialize(self):
        return {
            "input_source": self.input_source,
            "transforms": self.transforms,
            "windowing": self.windowing,
            "triggers": self.triggers,
            "resources": self.resources,
            "monitoring_hooks": self.monitoring_hooks,
        }

class SparkJobBuilder:
    def __init__(self):
        self._input_source = None
        self._transforms = []
        self._windowing = None
        self._triggers = None
        self._resources = {}
        self._monitoring_hooks = []

    def input_source(self, source):
        self._input_source = source
        return self
    
    def set_transforms(self, transforms):
        self._transforms = transforms
        return self
    
    def windowing(self, windowing):
        self._windowing = windowing
        return self
    
    def triggers(self, triggers):
        self._triggers = triggers
        return self

    def resources(self, resources):
        self._resources = resources
        return self
    
    def monitoring_hooks(self, hooks):
        self._monitoring_hooks = hooks
        return self
    
    def build(self):
        return SparkJobSpec(
            input_source=self._input_source,
            transforms=self._transforms,
            windowing=self._windowing,
            triggers=self._triggers,
            resources=self._resources,
            monitoring_hooks=self._monitoring_hooks
        )