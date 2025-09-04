"""Enhanced multi-query parallel retrieval system for MooseAgent."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS, Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
import asyncio
import re

from mooseagent.configuration import Configuration
from mooseagent.utils import load_chat_model, BGE_M3_EmbeddingFunction
from mooseagent.prompts import ENHANCED_RETRIEVAL_QUERY_PROMPT, CONTENT_REFINEMENT_PROMPT


class SearchQuestion(BaseModel):
    """A single search question for retrieval."""

    question: str = Field(description="The specific question to search for")
    priority: int = Field(description="Priority of the question (1-5, 5 being highest)")
    category: str = Field(description="Category of the question (e.g., 'geometry', 'physics', 'boundary', 'material')")


class RetrievalResult(BaseModel):
    """Result from a single retrieval query."""

    question: str = Field(description="The original question")
    content: str = Field(description="Retrieved content")
    relevance_score: float = Field(description="Relevance score (0-1)")
    key_points: List[str] = Field(description="Key points extracted from the content")


class EnhancedRetrievalState(BaseModel):
    """State for enhanced retrieval system."""

    questions: List[SearchQuestion] = Field(description="List of search questions")
    results: List[RetrievalResult] = Field(description="Retrieval results")
    summarized_content: str = Field(description="Summarized and refined content")


class EnhancedRetrievalSystem:
    """Enhanced multi-query parallel retrieval system."""

    def __init__(self, config: RunnableConfig):
        self.configuration = Configuration.from_runnable_config(config)
        self._setup_vector_stores()
        self._setup_models()

    def _setup_vector_stores(self):
        """Setup vector stores for retrieval."""
        embedding_function = (
            OpenAIEmbeddings() if self.configuration.embedding_function == "OPENAI" else BGE_M3_EmbeddingFunction()
        )

        vector_type = self.configuration.vector_store
        top_k = self.configuration.top_k

        try:
            if vector_type.lower() == "faiss":
                self.vectordb_input = FAISS.load_local(
                    self.configuration.input_database_path, embedding_function, allow_dangerous_deserialization=True
                )
                self.vectordb_dp = FAISS.load_local(
                    self.configuration.dp_database_path, embedding_function, allow_dangerous_deserialization=True
                )
            elif vector_type.lower() == "chroma":
                self.vectordb_input = Chroma(
                    persist_directory=self.configuration.input_database_path, embedding_function=embedding_function
                )
                self.vectordb_dp = Chroma(
                    persist_directory=self.configuration.dp_database_path, embedding_function=embedding_function
                )
            else:
                raise ValueError(f"Unsupported vector store type: {vector_type}")

            self.retriever_input = self.vectordb_input.as_retriever(
                search_type="similarity", search_kwargs={"k": top_k}
            )
            self.retriever_dp = self.vectordb_dp.as_retriever(search_type="similarity", search_kwargs={"k": top_k})

        except Exception as e:
            print(f"Error loading vector database: {e}")
            raise

    def _setup_models(self):
        """Setup language models for question generation and content refinement."""
        self.question_generator = load_chat_model(self.configuration.query_model)
        self.content_refiner = load_chat_model(self.configuration.rag_model)

    async def generate_search_questions(self, task_description: str) -> List[SearchQuestion]:
        """Generate targeted search questions based on task description."""

        human_prompt = f"""Based on the following simulation requirements, generate targeted search questions:

<Simulation Requirements>
{task_description}
</Simulation Requirements>

Generate search questions that will help find relevant MOOSE simulation cases and documentation.
Focus on different aspects like geometry, physics, boundary conditions, materials, etc.
"""

        try:
            response = await self.question_generator.ainvoke(
                [SystemMessage(content=ENHANCED_RETRIEVAL_QUERY_PROMPT), HumanMessage(content=human_prompt)]
            )

            # Parse the response to extract questions
            questions = self._parse_questions_from_response(response.content)
            return questions

        except Exception as e:
            print(f"Error generating search questions: {e}")
            # Fallback to basic question generation
            return [
                SearchQuestion(
                    question=f"MOOSE simulation case for {task_description[:100]}", priority=5, category="general"
                )
            ]

    def _parse_questions_from_response(self, response_content: str) -> List[SearchQuestion]:
        """Parse questions from model response."""
        questions = []

        # Try to extract structured questions
        question_patterns = [
            r"(\d+)\.\s*(.*?)(?=\n\d+\.|\n\n|$)",
            r"Question\s*(\d*):\s*(.*?)(?=\nQuestion|$)",
            r"-\s*(.*?)(?=\n-|\n\n|$)",
        ]

        for pattern in question_patterns:
            matches = re.findall(pattern, response_content, re.DOTALL)
            if matches:
                for i, match in enumerate(matches):
                    if isinstance(match, tuple):
                        question_text = match[1] if len(match) > 1 else match[0]
                    else:
                        question_text = match

                    question_text = question_text.strip()
                    if question_text and len(question_text) > 10:
                        questions.append(
                            SearchQuestion(
                                question=question_text,
                                priority=max(1, 5 - i),
                                category=self._categorize_question(question_text),
                            )
                        )
                break

        # If no structured format found, split by lines and clean
        if not questions:
            lines = [line.strip() for line in response_content.split("\n") if line.strip()]
            for i, line in enumerate(lines[:5]):
                if len(line) > 10:
                    questions.append(
                        SearchQuestion(question=line, priority=max(1, 5 - i), category=self._categorize_question(line))
                    )

        return questions[:7]  # Limit to 7 questions maximum

    def _categorize_question(self, question: str) -> str:
        """Categorize a question based on its content."""
        question_lower = question.lower()

        categories = {
            "geometry": ["mesh", "geometry", "domain", "grid", "dimension", "shape"],
            "physics": ["physics", "equation", "coupling", "multiphysics", "phenomenon"],
            "boundary": ["boundary", "bc", "condition", "constraint", "interface"],
            "material": ["material", "property", "parameter", "constant"],
            "solver": ["solver", "execution", "convergence", "time", "step"],
            "application": ["app", "module", "kernel", "variable"],
        }

        for category, keywords in categories.items():
            if any(keyword in question_lower for keyword in keywords):
                return category

        return "general"

    async def parallel_retrieve(self, questions: List[SearchQuestion]) -> List[RetrievalResult]:
        """Perform parallel retrieval for multiple questions."""

        async def retrieve_single_question(question: SearchQuestion) -> RetrievalResult:
            """Retrieve information for a single question."""
            try:
                # Retrieve from both databases
                input_docs = await self.retriever_input.ainvoke(question.question)
                dp_docs = await self.retriever_dp.ainvoke(question.question)

                # Combine and format results
                all_docs = []
                for doc in input_docs + dp_docs:
                    all_docs.append(doc.page_content)

                combined_content = "\n\n".join(all_docs)

                # Calculate relevance score (simplified)
                relevance_score = min(1.0, len(combined_content) / 1000)

                # Extract key points
                key_points = self._extract_key_points(combined_content)

                return RetrievalResult(
                    question=question.question,
                    content=combined_content,
                    relevance_score=relevance_score,
                    key_points=key_points,
                )

            except Exception as e:
                print(f"Error retrieving for question '{question.question}': {e}")
                return RetrievalResult(question=question.question, content="", relevance_score=0.0, key_points=[])

        # Execute retrievals in parallel
        tasks = [retrieve_single_question(q) for q in questions]
        results = await asyncio.gather(*tasks)

        # Filter out empty results and sort by priority
        valid_results = [r for r in results if r.content and r.relevance_score > 0.1]
        valid_results.sort(key=lambda x: x.relevance_score, reverse=True)

        return valid_results

    def _extract_key_points(self, content: str) -> List[str]:
        """Extract key points from retrieved content."""
        if not content or len(content.strip()) < 50:
            return []

        # Simple extraction based on line breaks and keywords
        lines = [line.strip() for line in content.split("\n") if line.strip()]

        key_points = []
        for line in lines[:10]:  # Limit to first 10 lines
            if len(line) > 20 and not line.startswith("#"):
                # Remove common prefixes
                cleaned = re.sub(r"^[-*•]\s*", "", line)
                cleaned = re.sub(r"^\d+\.\s*", "", cleaned)

                if len(cleaned) > 20:
                    key_points.append(cleaned)

        return key_points[:5]  # Return top 5 key points

    async def refine_and_summarize(self, results: List[RetrievalResult], task_description: str) -> str:
        """Refine and summarize retrieval results."""

        if not results:
            return "No relevant information found."

        # Prepare input for summarization
        input_text = f"Task: {task_description}\n\n"
        input_text += "Retrieved Information:\n"

        for result in results:
            input_text += f"\nQuestion: {result.question}\n"
            input_text += f"Key Points: {', '.join(result.key_points[:3])}\n"
            input_text += f"Content: {result.content[:500]}...\n"

        system_prompt = CONTENT_REFINEMENT_PROMPT

        try:
            response = await self.content_refiner.ainvoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=input_text)]
            )

            return response.content

        except Exception as e:
            print(f"Error refining content: {e}")
            # Fallback: simple concatenation of key points
            fallback_summary = "Key Information:\n"
            for result in results:
                if result.key_points:
                    fallback_summary += f"- {', '.join(result.key_points[:2])}\n"
            return fallback_summary

    async def enhanced_retrieve(self, task_description: str) -> str:
        """Main method for enhanced retrieval."""

        # Step 1: Generate search questions
        questions = await self.generate_search_questions(task_description)
        print(f"Generated {len(questions)} search questions")

        # Step 2: Parallel retrieval
        results = await self.parallel_retrieve(questions)
        print(f"Retrieved {len(results)} relevant results")

        # Step 3: Refine and summarize
        summarized_content = await self.refine_and_summarize(results, task_description)

        return summarized_content


# Factory function for easy integration
def create_enhanced_retrieval_system(config: RunnableConfig) -> EnhancedRetrievalSystem:
    """Create an enhanced retrieval system instance."""
    return EnhancedRetrievalSystem(config)
