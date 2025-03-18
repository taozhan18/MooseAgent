"""Define the state structures for the agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from langgraph.managed import IsLastStep
from typing_extensions import Annotated, List, Literal, TypedDict
from pydantic import BaseModel, Field


class FlowState(TypedDict):
    """Defines the architect of input card of moose state for the agent."""

    requirement: str
    file_list: dict[str, str]  # key is the file name, value is the detailed description
    detailed_description: str
    similar_cases: str
    inpcard: InpcardState
    grade: Literal["pass", "fail"]
    feedback: str
    dp_json: dict[str, str]
    run_result: str


class FileState(BaseModel):
    file_name: str = Field(description="The file name of the input card.")
    description: str = Field(description="The detailed description of this file.")


class ExtracterFileState(BaseModel):
    file_list: list[FileState] = Field(description="A list of file name and its detailed description.")


class SubtaskState(BaseModel):
    name: str = Field(description="The name of the sub-task.")
    retrieve: bool = Field(description="Whether to retrieve information from the database.")
    description: str = Field(description="The detailed description of the sub-task.")


class ExtracterSubtaskState(BaseModel):
    sub_tasks: list[SubtaskState] = Field(
        description="A list of sub-tasks with name, retrieve value, and detailed description."
    )


class OneFileState(TypedDict):
    name: str
    description: str
    sub_tasks: list[str]
    inpcard: str
    dp_json: dict[str, str]


# class AlignmentState(BaseModel):
#     detailed_description: str = Field(description="Provide a complete simulation description here")


class InpcardState(BaseModel):
    name: str = Field(
        description="The file name of the input card. Use previous input card name if it exists.",
    )
    overall_description: str = Field(
        description="Overall description of the input card.",
    )
    inpcard: str = Field(
        description="The input card for MOOSE simulation tasks with annotations.",
    )


class RAGState(BaseModel):
    similar_case: list[InpcardState] = Field(
        description="A list of MOOSE simulation cases.",
    )


class ReviewArchitectState(BaseModel):
    grade_architect: Literal["pass", "fail"] = Field(
        description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
    )
    feedback_architect: str = Field(
        description="Feedback after the review.",
    )


class ReviewWriterState(BaseModel):
    grade: Literal["pass", "fail"] = Field(
        description="Evaluation result indicating whether the response meets requirements ('pass') or needs revision ('fail')."
    )
    feedback: str = Field(description="Feedback after the review.")


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
