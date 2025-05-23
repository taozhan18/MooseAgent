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
    run_result: list[str]
    reason: list[str]
    review_count: int  # the number of reviews
    rearchitect_count: int
    history_error: str


class OneFileState(TypedDict):
    inpcard: FileState
    check: str  # check the file
    dp_json: dict[str, str]
    review_count: int  # 添加review计数器


class FileState(BaseModel):
    file_name: str = Field(description="The file name of the input card.")
    description: str = Field(description="The detailed description of this file.")


class ExtracterFileState(BaseModel):
    file_list: list[FileState] = Field(description="A list of file name and its detailed description.")


class ExtracterArchitectState(BaseModel):
    code_template: str = Field(description="The proposed MOOSE input card template here")
    retrieve_content: list[str] = Field(
        description="List the content that needs to be retrieved in unclear areas here."
    )


class InpcardContentState(BaseModel):
    inpcard: str = Field(
        description="The complete annotated input card of moose without any additional irrelevant explanations or characters."
    )


class InpcardState(dict):
    name: str
    overall_description: str
    code: str


class ReviewOneFileState(BaseModel):
    """
    The output state of the review agent.
    """

    filename: str = Field(description="The file name of the input card which has error.")
    error: str = Field(
        description="Provide the code for the incorrect part of the input card and provide the error message for this part of the code."
    )


class ModifyState(BaseModel):
    """
    The output state of the review agent.
    """

    filename: str = Field(description="The file name of the input card which has error.")
    error: str = Field(
        description="Provide the original error message, explain the reason for the error and the method of modification."
    )
    code: str = Field(description="The modified code of the input card.")


class QueryState(BaseModel):
    query: str = Field(description="The query to search for relevant information.")


class RearchitechState(BaseModel):
    """_summary_

    Args:
        BaseModel (_type_): _description_
    """

    rearchitect: str = Field(
        description="If you find that the above information keeps repeating an error, please reply with True, else reply False"
    )
    error: str = Field(description="point out the error and indicate the reason why the error persists")
