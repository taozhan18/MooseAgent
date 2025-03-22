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
    file_list: ExtracterFileState  # key is the file name, value is the detailed description
    feedback: str
    dp_json: dict[str, str]
    run_result: str
    reviews: ReviewState


class OneFileState(TypedDict):
    inpcard: FileState
    check: str  # check the file
    dp_json: dict[str, str]


class FileState(BaseModel):
    file_name: str = Field(description="The file name of the input card.")
    description: str = Field(description="The detailed description of this file.")


class ExtracterFileState(BaseModel):
    file_list: list[FileState] = Field(description="A list of file name and its detailed description.")


class SubtaskState(BaseModel):
    name: str = Field(description="The name of the sub-task.")
    retrieve: bool = Field(description="Whether to retrieve information from the database.")
    description: str = Field(description="The detailed description of the sub-task.")


class ExtracterArchitectState(BaseModel):
    code_template: str = Field(description="The proposed MOOSE input card template here")
    retrieve_content: list[str] = Field(
        description="List the content that needs to be retrieved in unclear areas here."
    )


# class AlignmentState(BaseModel):
#     detailed_description: str = Field(description="Provide a complete simulation description here")
class InpcardContentState(BaseModel):
    inpcard: str = Field(
        description="The complete annotated input card of moose without any additional irrelevant explanations or characters."
    )


class InpcardState(dict):
    name: str
    overall_description: str
    code: str


class ReviewState(BaseModel):
    files: list[ReviewOneFileState] = Field(
        description="List of input files with issues, each element in the list stores the name of the file with its error."
    )


class ReviewOneFileState(BaseModel):
    """
    The output state of the review agent.
    """

    filename: str = Field(description="The file name of the input card which has error.")
    error: str = Field(description="Identify the problematic parts in the document.")


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
