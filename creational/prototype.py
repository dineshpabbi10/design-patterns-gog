"""
Problem: In your ETL orchestration, you often need to create variations of complex pipeline configurations rapidly. Design
a prototype mechanism to clone pipeline job specs (or client config objects) and customize a few fields without rebuilding
from scratch.

Constraints & hints:
- Cloning should be efficient and allow shallow or deep copy semantics where appropriate.
- Preserve provenance metadata so clones record their origin.
- Useful for templated jobs or spinning up test instances of real jobs.

Deliverable: show how a `PipelineSpec` prototype can be copied and mutated safely before submission.
"""

from copy import deepcopy,copy

class PipelineSpec:
    def __init__(self, *, name:str, input_source:str, transforms:list[dict[str,str]], resources:dict[str,str], metadata:dict[str,str]=None):
        self.name = name
        self.input_source = input_source
        self.transforms = transforms  # list of transform functions or descriptions
        self.resources = resources  # dict of resource settings
        self.metadata = metadata or {}  # dict for provenance and other metadata

    def clone(self, deep:bool, **overrides):
        """Clone the current PipelineSpec, optionally overriding fields.

        Args:
            deep (bool): If True, perform a deep copy; otherwise, shallow copy.
            **overrides: Fields to override in the cloned object.
        
        Returns:
            PipelineSpec: A new instance of PipelineSpec with applied overrides.
        """
        if deep:
            new_spec = deepcopy(self)
        else:
            new_spec = copy(self)
        
        # Apply overrides
        for key, value in overrides.items():
            if(hasattr(new_spec, key)):
                setattr(new_spec, key, value)
            else:
                raise AttributeError(f"PipelineSpec has no attribute '{key}'")
        
        # Update provenance metadata
        new_spec.metadata['cloned_from'] = self.name
        
        return new_spec