from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import List, Optional
from src.llm.LLmModel import LLmModel
from src.logger import logger as logging
import traceback


# Define the nested data structures
class WorkExperience(BaseModel):
    company: str = Field(description="Name of the company")
    role: str = Field(description="Job title/role")
    duration: str = Field(description="Time period of employment")
    responsibilities: List[str] = Field(description="List of job responsibilities")
    achievements: List[str] = Field(description="List of achievements in the role")
    technologies: List[str] = Field(description="Technologies used in the role")


class Project(BaseModel):
    name: str = Field(description="Name of the project")
    description: str = Field(description="Description of the project")
    technologies: List[str] = Field(description="Technologies used in the project")
    contributions: List[str] = Field(
        description="Individual contributions to the project"
    )
    outcomes: List[str] = Field(description="Project outcomes and results")
    methodologies: List[str] = Field(description="Methodologies and approaches used")


class CVData(BaseModel):
    personal_information: str = Field(
        description="Candidate's personal details and information"
    )
    skills: List[str] = Field(description="List of technical and non-technical skills")
    work_experience: List[WorkExperience] = Field(
        description="List of work experiences"
    )
    projects: List[Project] = Field(description="List of projects")


class CVExtractor:
    def __init__(self, model_name: str = "gpt-3.5-turbo", temperature: float = 0):
        self.model = LLmModel.getLangchainChatModel()
        self.parser = JsonOutputParser(pydantic_object=CVData)

        # Create the prompt template
        self.prompt = PromptTemplate(
            template="""Extract and categorize the candidate information from the following CV content.
            Ensure all details are preserved without summarization.
            Include specific methodologies, technical implementations, and advanced techniques.
            
            CV Content: {cv_content}
            
            {format_instructions}
            
            If any section is not provided in the CV, use empty lists for array fields and "not provided" for string fields.
            """,
            input_variables=["cv_content"],
            partial_variables={
                "format_instructions": self.parser.get_format_instructions()
            },
        )

        # Create the processing chain
        self.chain = self.prompt | self.model | self.parser

    def extract_cv(self, cv_content: str) -> CVData | dict:
        """
        Extract CV information using LangChain and return structured data.

        Args:
            cv_content (str): The CV content to analyze

        Returns:
            CVData: Structured CV information as a Pydantic model

        Raises:
            ValueError: If the CV content cannot be processed
        """
        try:
            result = self.chain.invoke({"cv_content": cv_content})
            return result
        except Exception as e:
            print(f"Error extracting CV information: {str(e)}")
            logging.error(f"Error extracting CV information: {str(e)}")
            logging.error(traceback.format_exc())
            # Return empty structure if processing fails
            # throw the exception
            raise e

            return CVData(
                personal_information="not provided",
                skills=[],
                work_experience=[],
                projects=[],
            )
