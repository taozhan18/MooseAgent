"""Define the state structures for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.managed import IsLastStep
from typing_extensions import Annotated, List, Literal, TypedDict
from pydantic import BaseModel, Field


class ArchitectState(TypedDict):
    """Defines the architect of input card of moose state for the agent."""

    requirement: str
    overall_description: str
    structured_requirements: str
    retrieve_tasks: List[str]
    grade_architect: Literal["pass", "fail"]
    feedback_architect: str


class ArchitectOutputState(BaseModel):
    overall_description: str = Field(description="A more complete and specific simulation requirement")
    structured_requirements: str = Field(
        description="A list of modules required for the MOOSE input card.",
    )
    retrieval_tasks: List[str] = Field(
        description="A list of knowledge needs to be retrieved.",
    )


class WriterState(TypedDict):
    """Defines the writer of input card of moose state for the agent."""

    structured_requirements: str
    retrieve_tasks: List[str]
    documentation: str
    inpcard: InpcardState
    grade_inpcard: Literal["pass", "fail"]
    feedback_inpcard: str
    documents_inpcard: List[str]


class ModuleState(BaseModel):
    name: str = Field(
        description="Name for this module.",
    )
    description: str = Field(
        description="A detailed and quantitative descriptions of the content of this module needs to define.",
    )


class ReviewArchitectState(BaseModel):
    grade_architect: Literal["pass", "fail"] = Field(
        description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
    )
    feedback_architect: str = Field(
        description="Feedback after the review.",
    )


class ReviewWriterState(BaseModel):
    grade_writer: Literal["pass", "fail"] = Field(
        description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
    )
    feedback_writer: str = Field(description="Feedback after the review.")


class InpcardState(BaseModel):
    name: str = Field(
        description="The file name of the input card.",
    )
    inpcard: str = Field(
        description="The input card for MOOSE simulation tasks with annotations, and the annotation symbol is #. The encoding mode is utf-8",
    )


# class InpcardsState(BaseModel):
#     inpcards: List[InpcardState] = Field(
#         description="A list of input cards.",
#     )


# class ReviewState(BaseModel):
#     grade: Literal["pass", "fail"] = Field(
#         description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
#     )
#     feedback: str = Field(
#         description="Feedback on the review.",
#     )
