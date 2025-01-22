from fastapi import FastAPI, UploadFile, File, HTTPException
from PyPDF2 import PdfReader
import os
from typing import Optional, Dict, Any
import json
from pydantic import BaseModel
from .CvExtractor import CVExtractor
from src.constant import USER_DATA_PATH


class PDFProcessor:
    def __init__(self):
        self.output_dir = USER_DATA_PATH
        self.cvExtractor = CVExtractor()
        os.makedirs(self.output_dir, exist_ok=True)

    async def extract_text_from_pdf(self, file: UploadFile) -> str:
        """Extract text from uploaded PDF file"""
        try:
            # Create a temporary file to store the uploaded PDF
            temp_path = f"temp_{file.filename}"
            with open(temp_path, "wb") as temp_file:
                content = await file.read()
                temp_file.write(content)

            # Read PDF and extract text
            text = ""
            with open(temp_path, "rb") as pdf_file:
                pdf_reader = PdfReader(pdf_file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"

            # Clean up temporary file
            os.remove(temp_path)
            return text

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error processing PDF: {str(e)}"
            )

    def extract_contact_info(self, text: str) -> dict:
        """Extract key information from text"""
        try:
            # Use the CVExtractor to get structured information
            cv_data = self.cvExtractor.extract_cv(text)

            extracted_info = cv_data
            # Convert Pydantic model to dictionary format
            if isinstance(cv_data, BaseModel):
                extracted_info = cv_data.model_dump()

            # Add original text to the output
            extracted_info["original_text"] = text

            return extracted_info

        except Exception as e:
            print(f"Error in extract_contact_info: {str(e)}")
            raise e
            return {
                "personal_information": "not provided",
                "skills": [],
                "work_experience": [],
                "projects": [],
                "original_text": text,
            }

    def save_json(self, user_id: str, extracted_info: dict):
        file_path = os.path.join(self.output_dir, f"{user_id}.json")
        with open(file_path, "w") as f:
            json.dump(extracted_info, f, indent=4)

    def save_user_data(self, user_id: str, extracted_info: dict):
        """Save extracted information to user file"""
        file_path = os.path.join(self.output_dir, f"{user_id}.txt")

        with open(file_path, "w") as f:
            f.write("=== Extracted Resume Information ===\n\n")

            # Write personal information
            f.write("Personal Information:\n")
            f.write(f"{extracted_info['personal_information']}\n\n")

            # Write skills
            f.write("Skills:\n")
            for skill in extracted_info.get("skills", []):
                f.write(f"- {skill}\n")
            f.write("\n")

            # Write work experience
            if extracted_info.get("work_experience"):
                f.write("Work Experience:\n")
                for exp in extracted_info["work_experience"]:
                    f.write(f"\nCompany: {exp['company']}\n")
                    f.write(f"Role: {exp['role']}\n")
                    f.write(f"Duration: {exp['duration']}\n")

                    if exp.get("responsibilities"):
                        f.write("Responsibilities:\n")
                        for resp in exp["responsibilities"]:
                            f.write(f"- {resp}\n")

                    if exp.get("achievements"):
                        f.write("Achievements:\n")
                        for achievement in exp["achievements"]:
                            f.write(f"- {achievement}\n")

                    if exp.get("technologies"):
                        f.write("Technologies:\n")
                        for tech in exp["technologies"]:
                            f.write(f"- {tech}\n")

            # Write projects
            if extracted_info.get("projects"):
                f.write("\nProjects:\n")
                for project in extracted_info["projects"]:
                    f.write(f"\nName: {project['name']}\n")
                    f.write(f"Description: {project['description']}\n")

                    if project.get("technologies"):
                        f.write("Technologies:\n")
                        for tech in project["technologies"]:
                            f.write(f"- {tech}\n")

                    if project.get("contributions"):
                        f.write("Contributions:\n")
                        for contribution in project["contributions"]:
                            f.write(f"- {contribution}\n")

                    if project.get("outcomes"):
                        f.write("Outcomes:\n")
                        for outcome in project["outcomes"]:
                            f.write(f"- {outcome}\n")

                    if project.get("methodologies"):
                        f.write("Methodologies:\n")
                        for methodology in project["methodologies"]:
                            f.write(f"- {methodology}\n")

            # Write original text if available
            if "original_text" in extracted_info:
                f.write("\nOriginal Text:\n")
                f.write(extracted_info["original_text"])
