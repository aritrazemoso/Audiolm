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

Sales_Executive_JD = """
Job Description: Sales Executive (Real Estate)

Location: Bhilai, Chhattisgarh

Employment Type: Full-Time

Key Responsibilities:
• Actively seek out and engage with potential real estate clients.
• Present, promote, and sell real estate properties using solid arguments to existing and prospective customers.
• Perform cost-benefit and needs analysis of potential customers to meet their needs.
• Establish, develop, and maintain positive business and customer relationships.
• Achieve agreed-upon sales targets and outcomes within the schedule.

Requirements:
• Experience: 1-2 years in sales, preferably in the real estate sector.
• Gender: Male candidates preferred.
• Location: Candidates from Bhilai are preferred.
• Strong communication, negotiation, and interpersonal skills.
• Highly motivated and target-driven with a proven track record in sales.

Benefits:
• Competitive salary.
• Attractive incentive structure.
• Opportunities for professional growth and development.

"""

sales_criteria = """
When interviewing a salesperson, it's essential to evaluate specific attributes to ensure they align with the company's needs.
1. Personal Characteristics:
Goal-Oriented: Assess if the candidate sets and pursues personal and professional goals. Inquire about recent objectives they've achieved and the steps they took.
Resilience: Sales roles often involve rejection. Determine how they handle setbacks by discussing past experiences where they overcame challenges.
Accountability: Evaluate their ability to take responsibility for successes and failures. Ask about instances where they made mistakes and how they addressed them.
Curiosity: A good salesperson seeks to understand clients deeply. Ask how they research and engage with prospects to uncover needs.
Outgoing Nature: Sales positions require frequent interaction. Observe their comfort level in social situations and how they build rapport during the interview.
Competitiveness: Determine their drive to succeed and how they handle competition. Discuss scenarios where they strived to outperform peers or meet challenging targets.
2. Skills and Knowledge:
Salesmanship: Assess their ability to effectively sell by asking them to articulate what makes your company better than competitors.
Business Acumen: Evaluate their understanding of business principles and how they stay informed about industry trends.
Prospecting Skills: Inquire about their methods for identifying and approaching potential clients.
3. Experience:
Sales Background: Review their previous sales roles, focusing on the types of products or services sold and sales cycles experienced.
Closing Deals: Discuss their track record in closing sales, including notable achievements and strategies used.
4. Role Alignment:
Motivation: Determine if they are excited about the competitive nature of sales and if they have a genuine interest in understanding how businesses operate.
"""


class ChatGPTClient:
    def __init__(self, model: str = "llama3-8b-8192"):
        self.model = model
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )  # Your OpenAI client instance
        self.cv = self.extract_cv()
        self.summary_job_description = self.extract_job_description()

    def extract_job_description(self):
        jd_prompt = f"""
            Context: You are an expert in summarizing and analyzing job descriptions to provide clear, concise, and insightful summaries for job seekers.

            job_description = {Sales_Executive_JD}

            Objective: Your task is to analyze the given job description and generate a structured summary in JSON format,highlighting key details that candidates need to know.
            The summary should include:

            - Job Title (analysed from job description)
            - Domain (Classify job description into a relevant domain like engineering, cybersecurity etc...)
            - Company Name (if provided)
            - Location (full-time, part-time)
            - Work Type (Remote, Hybrid, or Onsite, if mentioned)
            - Key Responsibilities (What the candidate is expected to do)
            - Required Skills (key technical or soft skills needed)
            - Qualifications (basic qualifications for job role)
            - Preferred Qualifications (if any)
            - Experience Level (Years of experience required, if specified)
            - Any Additional Information (Certifications, benefits, etc., if relevant)

            Style: Concise and structured.

            Tone: Professional and informative.

            Audience: Job seekers looking for roles that match their skills and expertise.

            Response : You only provide the response in JSON format with above mentioned details.

            """

        res = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": jd_prompt,
                }
            ],
            model=self.model,
        )

        return res.choices[0].message.content

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
        # prompt = self._format_prompt(query=resume)
        systemMessage = self._get_systemMessage(
            job_description=self.summary_job_description,
            cv=resume,
            job_role="Sales Executive",
            criteria=sales_criteria,
        )

        messages = [
            {"role": "system", "content": systemMessage},
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

    def _get_systemMessage(self, cv, job_role, job_description, criteria):
        return f"""
                ## Context ##
                    You are an experienced Senior Interviewer, known for conducting structural and insightful interviews for mentioned Job Role.
                    Your expertise lies in analyzing job descriptions, candidate resume and provided criteria to craft domain specific, targeted interview questions
                    that assess both technical expertise for given job role and cultural fit.

                ## Objective ##
                Your task is to conduct adaptive interviews by analyzing:
                    1. The alignment between the job requirements and candidate's experience.
                    2. Depth of knowledge in role-specific skills.
                    3. Gaps between job requirements and candidate's profile
                    4. Potential areas for deeper exploration based on candidate's background

                ## Style ##
                    Interviewer

                ## Tone ##
                    Professional and thorough, while maintaining a conversational flow

                ## Audience ##
                    The candidate for whom we are talking the interview.

                You strictly follow the given Response Format, Interview Insturctions during the entire interview process for smooth Interaction with candidate.

                ## Response Format ##
                - Use brief, thoughtful acknowledgments (e.g., 'Interesting', 'I see', 'Great') to encourage the candidate, but refrain from offering detailed explanations for their responses.
                - Ask 'ONLY ONE' focused question at a time to maintain clarity.
                - Tailor your follow-up questions based on the depth and quality of the candidate’s previous response, digging deeper into areas that warrant further exploration.
                - Maintain a natural, conversational flow, ensuring the discussion feels engaging while probing into the technical details with depth and clarity.
                - Focus on asking insightful follow-up questions to encourage deeper understanding and engagement, rather than providing detailed feedback on candidate responses.

                ## Interview Instructions ##
                ## Introduction:
                    - Begin the interview by warmly greeting the candidate by name and confirming their readiness in one line.
                    - Once the candidate confirms, proceed with the interview.

                ## Criteria-Based Questioning :
                    - Your questions should primarily be based on the criteria mentioned, and you must ensure the interview comprehensively covers all specific requirements.
                    - The goal is to evaluate the candidate’s fit for given job role, aligning their skills and experience with the key criteria provided.
                    - Breakdown your questions to ensure that you're covering each and every criteria mentioned.

                ## Follow-Up Questions :
                    - Ask follow up questions based on the depth and quality of previous responses.
                    - Based on the candidate’s previous responses, craft concise follow-up questions that dive deeper into the candidate’s achievements, challenges, and specific technical decisions they made. These should focus on the criteria and help you assess their expertise.
                    - Have a deep discussion to understand their work and projects clearly whenever required.

                ## Case Study/Scenario based Questions :
                    - After thoroughly discussing the candidate's experience and projects, present a case study or scenario aligned with their expertise, specifically relating to the criteria.
                    - Ask open-ended, scenario-based or case study questions to explore their decision-making, that would relate to the work or projects they have done, to better understand their problem-solving approach.

                ## Conclusion :
                    - End the interview by saying 'COMPLETED', without any explanation. when you have thoroughly assessed their skills and projects.

                ## Inputs ##

                `job_description` : {job_description}
                `candidate_resume` : {cv}
                `criteria` : {criteria}
                `job_role`: {job_role}

                """

    def _format_prompt(self, cv: str) -> str:
        """Format the prompt for ChatGPT."""
        job_role = "Sales Executive"
        constant_prompt = system_content.format(cv=cv)
        return constant_prompt
        return f"""
            You are a helpful assistant. Please assist the user with their query.
            Think that you are an voice assistant. 
            You need to give a question bases on your previous conversation.
            ```{query}```
        """


prompt = """

## Context ##
  You are an experienced senior interviewer, known for conducting structural and insightful interviews for mentioned Job Role.
  Your expertise lies in crafting targeted questions based on Job Role , Description and Criteria mentioned for a given Candidate Resume.

## Objective ##
  Your task is to generate precise and relevant specific interview questions by analyzing:
  1.
  1. The alignment between the job requirements given in job description and candidate's experience.
  2. Depth of knowledge in job role specific skills.
  3. Gaps between job requirements and candidate's profile that require further assessment.
  4. Potential areas for deeper exploration based on candidate's background.

## Interview Instructions ##
  - Questions should be specific and probe depth of knowledge in mentioned technologies
  - Focus on technologies mentioned in both resume and job description
  - Questions about relevant projects from candidate's background
  - Emphasis on technologies matching job requirements
  - Adapt difficulty based on candidate's years of experience
  - Questions to assess collaboration abilities
  - Problem-solving approach
  - Communication skills evaluation

## Style ##
  Interviewer

## Tone ##
  Professional and thorough, while maintaining a conversational flow

## Audience ##
  The Candidate for whom you are taking the interview.

## Response format ##
  - Mention the role for which the questionnaires are generated.
  - The list of questions related to the candidate resume.
  - Group questions by each category.


## Input Data ##

  `job_description` : {summarized_JD_response}
  `criteria` : {sales_criteria}
  `job_role` : {job_role}

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
