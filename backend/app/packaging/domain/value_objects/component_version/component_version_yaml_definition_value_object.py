import json
import typing
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional, Union

import yaml
from pydantic import BaseModel, ConfigDict

from app.packaging.domain.exceptions import domain_exception


# Pydantic validation of EC2 Image Builder component YAML definition
# Ref: https://docs.aws.amazon.com/imagebuilder/latest/userguide/toe-use-documents.html
class ComponentStepYaml(BaseModel):
    name: str
    action: str
    timeoutSeconds: Optional[int] = 7200
    onFailure: Optional[Literal["Abort", "Continue", "Failed"]] = "Abort"
    maxAttempts: Optional[int] = 1
    inputs: Optional[Union[List, Dict]]  # This is not really required for all actions


class ComponentPhaseYaml(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Literal["build", "test", "validate"]
    steps: List[ComponentStepYaml]


class ComponentYaml(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    description: Optional[str] = None
    schemaVersion: str
    phases: List[ComponentPhaseYaml]


@dataclass(frozen=True)
class ComponentVersionYamlDefinitionValueObject:
    value: str


def from_str(value: typing.Optional[str]) -> ComponentVersionYamlDefinitionValueObject:
    if not value:
        raise domain_exception.DomainException("Component version YAML definition cannot be empty.")

    try:
        # Convert YAML to JSON
        component_json_str = json.loads(json.dumps(yaml.full_load(value)))
        ComponentYaml(**component_json_str)
    except:
        raise domain_exception.DomainException("Component version YAML definition is invalid.")

    return ComponentVersionYamlDefinitionValueObject(value=value)
