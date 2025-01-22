from typing import AsyncGenerator, Optional, Dict, Any
from openai import OpenAI
import os
from src.types import InterviewHistory
from typing import List

context_5_MJ_WO_Exp = """
  Expert in: Java, React , Javascript , Python

  Education

    B.Tech (2023)
    Indian Institute of Technology Kharagpur

  Awards

  1. Senior JBNSTS Scholar: Awarded the prestigious JBNSTS Scholarship, recognizing top academic and scientific talent among students in India.

  2. IIT JEE Advanced: Successfully passed the highly competitive IIT JEE Advanced exam, securing admission to the prestigious IIT Kharagpur.

  3. Board Ranks: Achieved Board Rank 9 in both Higher Secondary and Secondary exams, standing out among over 1 million students.

  Projects

  1. Expense Tracker - Developed a web-based Expense Tracker using React, enabling users to track expenses, categorize transactions, and view detailed reports. Enhanced usability and accessibility by integrating voice command functionality, allowing users to add expenses or income via voice commands.

  2. Music App - Developed a React-based web app that fetches songs by genre and location via third-party APIs, providing users with a personalized experience featuring top charts and artists. Integrated third-party APIs to dynamically fetch and display trending music and artist information across various regions, enhancing the app's functionality.
"""


class ChatGPTClient:
    def __init__(self, model: str = "llama3-8b-8192"):
        self.model = model
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )  # Your OpenAI client instance
        self.cv = self.extract_cv()

    def extract_cv(self, cv: str = context_5_MJ_WO_Exp):
        resume_context = f"""
        You are an agent in extracting the information for larger context, your task is to categorize the given
        information of candidate from the below context.
        Ensure that no details are omitted or summarized in a way that reduces clarity or richness.
        Include specific methodologies, technical implementations, and advanced techniques whenever mentioned.

        Context : {cv}

        # JSON Response Format #
        `personal_information` : 'Details such as the candidate's name and other relevant personal data.'
        `skills` : 'A list of all technical and non-technical skills mentioned, categorized where possible.'
        `work_experience`: 'Detailed descriptions of the candidate's previous roles, including responsibilities, achievements, and technologies used, without omitting any information.'
        `projects`: 'Comprehensive information about the candidate's projects, including project goals, technologies used, candidate contributions, outcomes, and methodologies. Highlight any advanced techniques or expertise demonstrated in these projects.'

        If particular section is not provides, mention them by giving 'not provided'
        """
        res = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": resume_context,
                }
            ],
            model=self.model,
        )
        # print(res.choices[0].message.content)
        return res.choices[0].message.content

    async def stream_response(
        self,
        query: str,
        resume: str,
        context: Optional[List[InterviewHistory]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream response from ChatGPT."""
        prompt = self._format_prompt(query=resume)

        messages = [
            {"role": "system", "content": prompt},
        ]

        for response in context:
            messages.append(
                {
                    "role": response.role,
                    "content": response.content,
                }
            )

        # if context:
        #     prompt += "\nContext:\n"
        #     for response in context:
        #         prompt += f"\n{response.role}: {response.content}"
        #     prompt += "\n\n"

        print(prompt)
        chat_completion = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            stream=True,
        )

        for chunk in chat_completion:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _format_prompt(self, query: str) -> str:
        """Format the prompt for ChatGPT."""
        constant_prompt = system_content.format(cv=query)
        return constant_prompt
        return f"""
            You are a helpful assistant. Please assist the user with their query.
            Think that you are an voice assistant. 
            You need to give a question bases on your previous conversation.
            ```{query}```
        """


system_content = """
      You are an experienced technical interviewer with 20 years of experience conducting adaptive interviews.

      Review the candidate information
      Candidate_info: ```{cv}```

      You must strictly follow the given Interview guidelines , response format during the
      entire interview process for smooth Interaction with candidate.

      ## Response Format

      - Use brief, thoughtful acknowledgments (e.g., 'Interesting', 'I see', 'Great') to encourage the candidate, but refrain from offering detailed explanations for their responses.
      - Ask 'ONLY ONE' focused question at a time to maintain clarity.
      - Tailor your follow-up questions based on the depth and quality of the candidate’s previous response, digging deeper into areas that warrant further exploration.
      - Maintain a natural, conversational flow, ensuring the discussion feels engaging while probing into the technical details with depth and clarity.

      ## Interview Guidelines

      - Striclty Start by warmly greeting the candidate and confirming their readiness in one line.
      - Instead of directly asking about the skills listed in the resume, connect those skills to the candidate's work experience's and projects, and ask how they applied them in real-world scenario.
      - If a skill mentioned in the resume is not implemented in any of the projects or experiences, ask the candidate where and how they have used that skill.
      - Ask open-ended, scenario-based or case study questions to explore their decision-making, that would relate to the work or projects they have done, to better understand their problem-solving approach.
      - Craft concise, engaging follow-up questions that delve deeper into the candidate's specific achievements or challenges, emphasizing quantitative outcomes and practical implementations and avoid overly broad or introductory questions, focusing instead on technical depth and actionable insights.

      ## Interview Flow

      1. If both projects and experiences are present, prioritize experiences first and then projects if necessary.
      2. If candidate has no experience mentioned :
        - Start with project-related questions. Also ask questions from Data Structures, Algorithms, and advanced problem-solving scenarios.
        - Ask scenario-based questions that require a combination of DSA knowledge and problem-solving skills.
      3. For each significant project:
        - Ask about their specific role and contributions.
        - Follow up on technical decisions and challenges mentioned.
        - Explore the technologies they used in context.
      4. For each work experience :
        - Ask about responsibilities and technical challenges.
        - Connect work experience with skills mentioned.
        - Discuss specific technical implementations.
      5. Have a deep discussion to understand their work and projects clearly whenever required.
      6. Ask follow up questions based on the depth and quality of previous responses.
      7. After completing the experience and projects discussion , you present a case study or scenario that aligns with the
         candidate's domain or based on the work that candidate was part of and ask follow up if required.

    End the interview by saying 'COMPLETED', without any explanation. when you have thoroughly assessed their skills and projects.

    Remember: Your goal is to understand both their knowledge breadth and depth through adaptive questioning, Maintain natural conversation throughout the interview.

    """
