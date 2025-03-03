"""Define the state structures for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.managed import IsLastStep
from typing_extensions import Annotated, List, Literal, TypedDict
from pydantic import BaseModel, Field


class ArchitectInputState(TypedDict):
    """Defines the input card of moose state for the agent."""

    topic: str


class ArchitectOutputState(TypedDict):
    """Defines the output card of moose state for the agent."""

    modules: ModulesState


class ArchitectState(TypedDict):
    """Defines the architect of input card of moose state for the agent."""

    topic: str
    modules: ModulesState
    grade_architect: Literal["pass", "fail"]
    feedback_architect: str


class WriterState(TypedDict):
    """Defines the writer of input card of moose state for the agent."""

    modules: ModulesState
    inpcard: InpcardState
    grade_inpcard: Literal["pass", "fail"]
    feedback_inpcard: str


class ModuleState(BaseModel):
    name: str = Field(
        description="Name for this module.",
    )
    description: str = Field(
        description="A detailed and quantitative descriptions of the content of this module needs to define.",
    )


class ModulesState(BaseModel):
    overall_architect: str = Field(description="A clear description of the simulation task")
    modules_description: List[ModuleState] = Field(
        description="A list of modules required for the MOOSE input card.",
    )


class ReviewState(BaseModel):
    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
    )
    feedback: str = Field(
        description="Feedback on the review.",
    )


class InpcardState(BaseModel):
    name: str = Field(
        description="The file name of the input card.",
    )
    inpcard: str = Field(
        description="The input card for the MOOSE simulation task. The encoding mode is utf-8",
    )


# class ReviewState(BaseModel):
#     grade: Literal["pass", "fail"] = Field(
#         description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
#     )
#     feedback: str = Field(
#         description="Feedback on the review.",
#     )
