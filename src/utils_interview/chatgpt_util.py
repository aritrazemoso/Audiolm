from typing import AsyncGenerator, Optional, Dict, Any
from openai import OpenAI
import os
from src.types import InterviewHistory
from typing import List

# context_5_MJ_WO_Exp = """
#   Expert in: Java, React , Javascript , Python

#   Education

#     B.Tech (2023)
#     Indian Institute of Technology Kharagpur

#   Awards

#   1. Senior JBNSTS Scholar: Awarded the prestigious JBNSTS Scholarship, recognizing top academic and scientific talent among students in India.

#   2. IIT JEE Advanced: Successfully passed the highly competitive IIT JEE Advanced exam, securing admission to the prestigious IIT Kharagpur.

#   3. Board Ranks: Achieved Board Rank 9 in both Higher Secondary and Secondary exams, standing out among over 1 million students.

#   Projects

#   1. Expense Tracker - Developed a web-based Expense Tracker using React, enabling users to track expenses, categorize transactions, and view detailed reports. Enhanced usability and accessibility by integrating voice command functionality, allowing users to add expenses or income via voice commands.

#   2. Music App - Developed a React-based web app that fetches songs by genre and location via third-party APIs, providing users with a personalized experience featuring top charts and artists. Integrated third-party APIs to dynamically fetch and display trending music and artist information across various regions, enhancing the app's functionality.
# """

# Sales_Executive_JD = """
# Job Description: Sales Executive (Real Estate)

# Location: Bhilai, Chhattisgarh

# Employment Type: Full-Time

# Key Responsibilities:
# • Actively seek out and engage with potential real estate clients.
# • Present, promote, and sell real estate properties using solid arguments to existing and prospective customers.
# • Perform cost-benefit and needs analysis of potential customers to meet their needs.
# • Establish, develop, and maintain positive business and customer relationships.
# • Achieve agreed-upon sales targets and outcomes within the schedule.

# Requirements:
# • Experience: 1-2 years in sales, preferably in the real estate sector.
# • Gender: Male candidates preferred.
# • Location: Candidates from Bhilai are preferred.
# • Strong communication, negotiation, and interpersonal skills.
# • Highly motivated and target-driven with a proven track record in sales.

# Benefits:
# • Competitive salary.
# • Attractive incentive structure.
# • Opportunities for professional growth and development.

# """

# sales_criteria = """
# When interviewing a salesperson, it's essential to evaluate specific attributes to ensure they align with the company's needs.
# 1. Personal Characteristics:
# Goal-Oriented: Assess if the candidate sets and pursues personal and professional goals. Inquire about recent objectives they've achieved and the steps they took.
# Resilience: Sales roles often involve rejection. Determine how they handle setbacks by discussing past experiences where they overcame challenges.
# Accountability: Evaluate their ability to take responsibility for successes and failures. Ask about instances where they made mistakes and how they addressed them.
# Curiosity: A good salesperson seeks to understand clients deeply. Ask how they research and engage with prospects to uncover needs.
# Outgoing Nature: Sales positions require frequent interaction. Observe their comfort level in social situations and how they build rapport during the interview.
# Competitiveness: Determine their drive to succeed and how they handle competition. Discuss scenarios where they strived to outperform peers or meet challenging targets.
# 2. Skills and Knowledge:
# Salesmanship: Assess their ability to effectively sell by asking them to articulate what makes your company better than competitors.
# Business Acumen: Evaluate their understanding of business principles and how they stay informed about industry trends.
# Prospecting Skills: Inquire about their methods for identifying and approaching potential clients.
# 3. Experience:
# Sales Background: Review their previous sales roles, focusing on the types of products or services sold and sales cycles experienced.
# Closing Deals: Discuss their track record in closing sales, including notable achievements and strategies used.
# 4. Role Alignment:
# Motivation: Determine if they are excited about the competitive nature of sales and if they have a genuine interest in understanding how businesses operate.
# """


IT_Specialist_Criteria = """
IT Specialist criteria, preserving all key responsibilities and intent:

**Responsibilities:**

* Maintain and monitor systems, infrastructure, and networks
* Ensure security, compliance, and backup/disaster recovery
* Administer networks, automate tasks, and optimize performance
* Provide user support, training, and project management
* Develop and implement policies, and manage vendors/licenses
* Document and report on IT activities, and lead/mentor others
* Research and innovate, and manage incidents and projects

**Technical Skills:**

* System monitoring, virtualization, cloud infrastructure, and storage solutions
* Security tools, IAM systems, backup tools, and scripting languages
* Configuration management, network devices, and performance optimization

**Soft Skills:**

* Problem-solving, analytical, and communication skills
* Leadership, mentorship, project management, and time management
* Collaboration, adaptability, attention to detail, and organizational skills

**Industry Knowledge:**

* Industry standards, emerging technologies, IT policies, and organizational goals
* Regulatory requirements and ability to stay updated with industry trends

**Senior System Administrator Requirements:**

* Strong technical expertise, leadership, and mentorship abilities
* Excellent problem-solving, communication, and time management skills
* Ability to prioritize tasks, lead projects, and collaborate with cross-functional teams.
"""



job_description = """

About the job
We are Lenovo. We do what we say. We own what we do. We WOW our customers.

Lenovo is a US$57 billion revenue global technology powerhouse, ranked #248 in the Fortune Global 500, and serving millions of customers every day in 180 markets. Focused on a bold vision to deliver Smarter Technology for All, Lenovo has built on its success as the world’s largest PC company with a full-stack portfolio of AI-enabled, AI-ready, and AI-optimized devices (PCs, workstations, smartphones, tablets), infrastructure (server, storage, edge, high performance computing and software defined infrastructure), software, solutions, and services. Lenovo’s continued investment in world-changing innovation is building a more equitable, trustworthy, and smarter future for everyone, everywhere. Lenovo is listed on the Hong Kong stock exchange under Lenovo Group Limited (HKSE: 992) (ADR: LNVGY).

This transformation together with Lenovo’s world-changing innovation is building a more inclusive, trustworthy, and smarter future for everyone, everywhere. To find out more visit www.lenovo.com, and read about the latest news via our StoryHub.

Overview

IT Product Analysis Specialist/IT Development Specialist role is critical in the solution implementation lifecycle cutting across all phases. The IT Product Analysis Specialist/IT Development Specialist has a deep understanding of technology and an ability to apply it to design solutions that meet the objectives of our customer.

The role of the IT Product Analysis Specialist/IT Development Specialist is to



Help customers build on their current CRM Custom solutions by expanding its use across the business through the latest technologies,
Execute designs under the guidance of a solution architect,
To configure and customize new solutions by leveraging the D365 CE, Power Platform Azure technologies along with other custom components.


Responsibilities


Website and CRM application designing, building, or maintaining.
Write C# or Java or Front End (JavaScript/React/Vue) code that is clean, efficient, scalable, and dependable.
Build and maintain the Rest/Soap APIs
Maintain frequent communication with team members and work closely with them throughout the development process.
Maintaining an understanding of the latest Web applications and programming practices through education, study, and participation in conferences, workshops, and groups.
Identifying problems uncovered by customer feedback and testing and correcting or referring problems to appropriate personnel for correction.
Evaluating code to ensure it meets industry standards, is valid, is properly structured, and is compatible with browsers, devices, or operating systems.
Determining user needs by analyzing technical requirements.
Knowledge of JS libraries like React or Vue and Microsoft/Salesforce CRM is a big plus. Proficiency in programming languages - C# or Java, Front End stack
Practical experience in translating business requirements into well-architected solutions that best leverage the D365 CE platform capabilities,
Ability to independently lead technical design sessions and develop detailed technical solution documentation that is aligned with current business objectives and the application landscape,
Document, develop and test working solutions, integrations, and data migration elements of D365 CE applications,
Demonstrable ability to leverage standard D365 features and ability to identify conditions when D365 should be customized. Ability to successfully communicate this information to both the customers and technical stakeholders,
Design and develop D365 components and 3rd-party integrations in accordance with Lenovo standards,
Design forms, workflow processes, flows, web services, plugins, canvas apps, model driven apps and other components needed to meet the business requirements obtained from customers,
Experience in building custom applications, modifications, integrations, data conversion routines, workflows, and custom reports for D365,
Executing ongoing maintenance of developed systems,
Executing on the architectural vision, goals, standards, structure, behavior patterns, models as defined by the solution architect,
Experience working with data migration for D365,
Excellent analytical, communication and technical skills combined with excellent planning and organizational skills, etc.


Professional Experience


2 – 5+ years of experience in CRM (D365/Salesforce/ServiceNow/Custom) with extensive industry knowledge,
Dynamics 365 Customer Engagement and knowledge of other Dynamics 365 apps,
Experience in leveraging the MS Power Azure Platform,
Implementation of Dynamics 365 CE (and prior versions) in an organization with more than 1k users,
Working with a solution architect to recommend a highly available, scalable Dynamics 365 architecture,
Experience in Java, C#.Net, Java Script, MS SQL, MS CRM SDK, MSD developer toolkit, SSRS, SSIS, etc.,
Knowledge of integration architecture and the ability to map integration pattern to functional usage,
Extensive experience in the implementation of MS CRM 3rd party Integration using Middleware Tools/ API’s (REST, ODATA Web API’s)/SSIS packages and/or connectors,
Experience in using Azure services for integration, Power Apps and Power Automate for upstream/downstream systems integrations,
Experience in the migration of large complex data sets – specifically data analysis, data cleansing, and data mappings using standard and 3rd-party tools e.g. Kingswaysoft SSIS,
Experienced in reporting architecture using SSRS and/orPower BI,
Should have excellent problem solving and analytical skills,
Advocate best practices to develop scalable solutions in alignment with Product roadmap through supported and upgradable customizations / implementations,
Experience in Agile and Waterfall delivery methodologies.


Qualification


Business / Industry Experience with specialization in an enterprise-wide CRM technology


2-5+ years of experience, ideally in Services, Business management or IT management,
2-5+ years of experience in D365 CE configuration and customization,
2+ years of experience in information intensive industries or digitally advanced enterprises,


Education


Bachelor’s or master’s degree in computer science/ engineering or related fields,
Relevant Dynamics 365 or prior certifications,
Relevant Power Platform or Azure certifications.


#BASD


We are an Equal Opportunity Employer and do not discriminate against any employee or applicant for employment because of race, color, sex, age, religion, sexual orientation, gender identity, national origin, status as a veteran, and basis of disability or any federal, state, or local protected class.
"""

class ChatGPTClient:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            # base_url="https://api.groq.com/openai/v1",
        )  # Your OpenAI client instance
        # self.cv = self.extract_cv()
        self.summary_job_description = self.extract_job_description()

    def extract_job_description(self):
        jd_prompt = """
            ## Context ##
            You are an expert in summarizing and analyzing job descriptions to provide clear, concise, and insightful summaries for job seekers.


            ## Objective ##
            Your task is to analyze the given job description and generate a structured summary in JSON format,highlighting key details that candidates need to know.
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


            ## Style ##
            Concise and structured.


            ## Tone ##
            Professional and informative.


            ## Audience ##
            Job seekers looking for roles that match their skills and expertise.


            ## Response ##
            You only provide the response in JSON format with above mentioned details.


            ## Inputs ##


            `job_description` = {job_description}
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

    def extract_cv(self, cv):
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

    def _get_validator_prompt(
      self, 
      question: str,
      job_role: str,
      job_criteria: dict,
      candidate_resume: dict,
      candidate_response: str
  ) -> str:
      return f"""
        You are an advanced AI-powered interview question validator and generator, leveraging the **Tree of Thought (ToT)** reasoning to validate provided **questions** against given **job_criteria and job_role**, the **candidate_resume**, and the latest **candidate_response**.


        Your role is to **assess the validity** of a given interview question and, if necessary, **reframe** it to ensure alignment with job expectations and the candidate’s background.
        If the question is valid, return it as it is, without any modifications.


        Your approach involves **dynamic branching** based on the provided question, exploring various **'thought paths'** to validate and generate the questions.
        Your primary task is to assess whether the question is valid based on the following thought process:


        ### **Tree of Thought Validation and Generation Instructions** ###


        ### Step 1 : **Question Categorization** ###
        - Determine whether the question belongs to one or more of the following categories:
          1. **Job Criteria-Based Validation** : Questions related to any of the key responsibilities, technical or soft skills, or tools mentioned in the provided job criteria directly or indirectly.
          2. **Resume Relevance** : Ensure the question is relevant to the candidate’s experience, skills, or qualifications as listed in their resume directly or indirectly.
          3. **Contextual Continuity**: If a prior candidate response exists, check if the question logically follow as a continuation or follow-up.
          4. **Opening Questions** : If the **question serves as an introduction** (e.g., "Tell me about yourself" ), validation is not required. Simply **return original question** without even modifying the acknowledgement.
          5. **Closing Question**  : If the question contains end of the interview with the word **'INTERVIEW COMPLETED'** , then do not reframe the question, simply return original question or text as it is.
          6. **Topic Switching**   : The question shifts between different topics while maintaining relevance to the interview. While the question may not be directly tied to the candidate's previous response, it transitions smoothly to another relevant subject.
        - Each question should be assessed based on these categories to ensure relevance, logical flow, and alignemnt with the interview context.


        ### Step 2 : **Multi-Path Question Validation** ###
        - Before validating the question, Throughly check and validate if provided question aligns with above categories.
          - Path A (Valid Question) :
            - If the question aligns with **at least one** of the above categories, it is considered valid.
            - Directly return the original question **without any modifications.**


          - Path B (InValid Question) :
            - If misalignment is found in **job criteria, resume relevance or logical continuity**, the question is considered as invalid.
            - Identify the exact reason for misalignment.




        ### Step 3 : **Thought Expansion for Question Generation and Adjusting Acknowledgement** ###
        - After Validating the questions, refine  or regenerate it based on its validity. Also, assess the acknowledgment at the beginning and adjust it to ensure alignment with the candidate’s previous response.
          - Path A: The Question is Valid
            - Preserve the original question exactly as it is.
            - **Modify only the acknowledgment** at the beginning if it unintentionally provides feedback, evaluation, or commentary on the candidate’s response.
            - **Do not modify acknowledgments** if they are interactive and naturally engage the candidate (e.g., “Interesting,” “I see,” “Great,” “Let’s move forward,” “Thanks for sharing,” “Let’s dive deeper”).
            - **Do not adjust acknowledgments** for introduction or opening questions.
            - **Example 1 (Adjusting Feedback-Based Acknowledgment)**
                **Original Question**:
                  "That's a solid problem-solving example. Lastly, how do you foster collaboration and communication within a cross-functional team during a project, especially when working with non-technical stakeholders?"
                **Refined Version (Adjusted Acknowledgment)**:
                  "On that note, how do you foster collaboration and communication within a cross-functional team during a project, especially when working with non-technical stakeholders?"
            - **Example 2 (Preserving Interaction kid of Acknowledgments)**
                **Original Question**:
                  "Thanks for sharing, Rajesh. Let's dive deeper into your recent work experience. Can you describe a specific project where you implemented CRM solutions, and what technical challenges you faced during the process?"
                **Returned Response**:
                  "Thanks for sharing, Rajesh. Let's dive deeper into your recent work experience. Can you describe a specific project where you implemented CRM solutions, and what technical challenges you faced during the process?"


          - Path B : The Question  is InValid
            - Identify missing context, incorrect focus, or misalignment with the candidate’s response, job criteria, or resume.
            - Reframe the question to ensure it remains relevant while maintaining conversational flow.
            - Add a brief and natural acknowledgment or transition at the beginning to create a smooth interview experience.
            - Use concise acknowledgments (e.g., “Interesting,” “I see,” “Great,” “Let’s move forward,” “Thanks for sharing,” “Let’s dive deeper”) to keep the conversation engaging without over-explaining the candidate’s response.


        ## Response Format ##
          - Respond **only with the refined question—either the original question (if valid) or the revised version (if invalid).**
          - **Do not provide explanations or justifications**.


        ### Inputs ###


        `question` : {question},
        `job_role` : {job_role},
        `job_criteria` : {job_criteria},
        `candidate_resume` : {candidate_resume},
        `candidate_response` : {candidate_response}
        
        """

      
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
            job_role="IT Product Analysis Specialist/IT Development Specialist",
            criteria=IT_Specialist_Criteria,
        )
        
        print("query is : ", query)
        
        print("Candidate resume : ", resume)

        system_messages = [
            {"role": "system", "content": systemMessage},
        ]

        for response in context:
            system_messages.append(
                {
                    "role": response.role,
                    "content": response.content,
                }
            )


        system_response  = self.client.chat.completions.create(
            messages=system_messages,
            model=self.model,
            stream=False,
        )
        
        # print("System response : ", system_response)
          
        print("Initial System response : ", system_response.choices[0].message.content)
        
        llm_validator_prompt = self._get_validator_prompt(
            question=system_response.choices[0].message.content,
            job_role="IT Product Analysis Specialist/IT Development Specialist",
            job_criteria=IT_Specialist_Criteria,
            candidate_resume=resume,
            candidate_response= ""
        )
        
        # print("LLM Validator Prompt : ", llm_validator_prompt)
        llm_validator_messages = [
            {"role": "system", "content": llm_validator_prompt},
        ]

        for response in context:
            llm_validator_messages.append(
                {
                    "role": response.role,
                    "content": response.content,
                }
            )


        llm_validator_response  = self.client.chat.completions.create(
            messages=llm_validator_messages,
            model=self.model,
            stream=True,
        )
        
        for chunk in llm_validator_response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def _get_systemMessage(self, cv, job_role, job_description, criteria):
        return f"""
            Your name is **'SAM'** an experienced AI Interviewer known for conducting structured , adaptive interviews for the provided job role. Begin with a fundamental technical question and branch into multiple paths depending on the candidate's responses.
            Incorporate behavioral and scenario-based questions as the conversation evolves.
            Keep adjusting based on the candidate's performance.

            You **Strictly** follow the given Response Format, Interview Instructions during the entire interview process for smooth interaction with candidates.

            ### Response Format ###
            - Use brief, thoughtful one line acknowledgments (like ...'Interesting', 'I see', 'Great','let's move forward','Thanks for sharing','let's dive deeper', etc...) to encourage the candidate before moving to next question, but avoid giving detailed explanations for their responses.
            - Ask **ONLY ONE** focused question at a time to maintain clarity.
            - Maintain a **professional and interactive tone** , ensuring a smooth conversational flow while focusing solely on the interview.
            - Tailor your **follow-up questions** based on the depth and quality of the candidate’s previous response, digging deeper into areas that require further exploration.
            - **You will not provide any additional context or details beyond the question.**
            - **You Strictly will NOT PROVIDE any commentary , feedback or summarization** to the candidate's answers.
            - You maintain **Professional, Interactive and Engaging conversational flow** throughout the conversation.


            ### Interview Structure ###


            ### Step 1 : Understanding Inputs
            - **Resume Analysis** : Extract key skills , experience and projects from candidate's resume.
            - **Job Description and Role** : analyse key skills, responsibilities , qualification requirements in the given job description for a mentioned job role.
            - **Criteria** : Analyse key objectives, responsibilities and skills to assess the candidate's suitability for the position.


            ### Step 2 : Introduction
            ## Introduction Question :
            - **Begin the interview with a concise introduction about yourself, followed by a warm welcome that sets the stage for a focused discussion on the candidate’s technical expertise aligned with the role they applied for.**
            - **Set expectations by instructing the candidate to provide clear responses and avoid giving long pauses to ensure a smooth interview process.**


            ## Opening Question :
            - **Warmly greet the candidate by confirming their readiness in a concise manner.**
            - **After confirming, ask the candidate to give a short introduction about themselves and overview of background and experience.**


            ### Step 3 : Adaptive Branching
            ## Branch 1 : Resume-Based Questions
              - Ask about recent work experience, how they implemented mentioned skills in their projects , any technical challenges faced.


            ## Branch 2 : Criteria-Based Questions
              - Ensure all interview questions are strictly aligned with the provided criteria, assessing the candidate’s skills, knowledge, and experience as per the job requirements.
              - The goal is to evaluate the candidate’s fit for a given job role, aligning their skills and experience with the key criteria provided from their resume.
              - Questions should directly relate to the candidate's resume while maintaining a strong focus on the specified criteria.
              - Cover all aspects of the given criteria, ensuring that no key competency is left unassessed.


            ## Branch 3 : Scenario-Based Questions
              - Ask open-ended, scenario-based or case study questions to explore their decision-making, that would align to the work or projects they have done, to better understand their problem-solving approach and how they apply knowledge in real-world situations.


            ## Branch 4 : Follow-Up Questions
              - For each of the questions in each branch ask follow up questions, based on the candidate's responses.
              - Adapt the complexity and nature of the questions according to the candidate’s responses.
              - Ask about relevant projects and work experiences from the candidate’s background, assessing their role, contributions, challenges faced, and solutions implemented.
              - Adjust the complexity of questions based on the candidate’s years of experience, ensuring an appropriate challenge level to accurately measure their expertise.


            ### Step 4 : Evaluation and Backtracking
              - If the candidate's answer lacks sufficient detail or clarity, backtrack to simpler or clarifying questions.
              - If the candidate struggles to answer any particular question or give incomplete answers, then ask clarifying follow up questions.
              - If the candidate shows strong understanding , then shift to other criteria mentioned.
              - Have a deep discussion to understand their work and projects clearly whenever required.


            ### Step 5 : Conclusion
              - Once all relevant areas have been assessed, conclude the interview with **'INTERVIEW COMPLETED!! Thanks for taking the time to interview with us! We will reach out to you with next steps shortly'** (without any further explanation).


            #Inputs
            `job_description` : {job_description}
            `candidate_resume` : {cv}
            `criteria` : {criteria}
            `job_role`: "IT Product Analysis Specialist/IT Development Specialist"
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
