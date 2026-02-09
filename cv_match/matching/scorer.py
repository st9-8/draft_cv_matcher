import logging
from typing import Dict, List, Tuple
from pydantic import BaseModel, Field

from django.conf import settings

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama

from traceback_with_variables import format_exc

from matching.models import CV
from matching.models import JobOffer

from matching.extractor import Extractor

logger = logging.getLogger(__name__)


class ScoringData(BaseModel):
    experience: float = Field(default=0,
                              description='Experience score based on the deterministic score but adjusted by you (0-100)')
    skills: float = Field(default=0,
                          description='Skills score based on the deterministic score but adjusted by you (0-100)')
    education: float = Field(default=0,
                             description='Education score based on the deterministic score but adjusted by you (0-100)')
    languages: float = Field(default=0, description='Languages score given by you (0-100)')
    job_fit: float = Field(default=0, description='Job fit score given by you (0-100)')

    score_comments: List[str] = Field(...,
                                      description='For each adjusted score, explain in 2 lines max why you adjusted it as you did.')
    strengths: List[str] = Field(..., description='Strengths (bonus XP, high qualifications, certificates, etc.)')
    weaknesses: List[str] = Field(..., description='Points to watch out for or weaknesses')
    missing_skills: List[str] = Field(..., description='Key skills lacking in relation to supply')
    summary: str = Field(..., description='Overall summary and final opinion of the recruiter')


class GlobalScorer:
    def __init__(self, offer: JobOffer, cv: CV):
        self.extractor: Extractor = Extractor(cv)
        self.offer: JobOffer = offer
        self.deterministic_score: Dict[str, float] = {}

        try:
            self.extractor.semantic_extract()
        except Exception as e:
            logger.error(format_exc(e))
            raise e

        if settings.EXTRACTION_MODEL_PROVIDER == 'openai':
            self.llm = ChatOpenAI(model=settings.EXTRACTION_MODEL, temperature=0)
        elif settings.EXTRACTION_MODEL_PROVIDER == 'anthropic':
            self.llm = ChatAnthropic(model=settings.EXTRACTION_MODEL, temperature=0)
        elif settings.EXTRACTION_MODEL_PROVIDER == 'ollama':
            self.llm = ChatOllama(model=settings.EXTRACTION_MODEL, temperature=0)
        else:
            self.llm = None

        self.weights = {
            'experience': 0.25,
            'skills': 0.35,
            'education': 0.10,
            'languages': 0.10,
            'job_fit': 0.20,
        }

        logger.info(f'Loaded global extractor with weights: {self.weights}')

    def _score_experience(self) -> float:
        """
            Score the candidate experience comparing to the offer required experience

            Rule:
            - 100% if greater or equal to required experience
            - Rule of 3 if lest than required experience
        """

        if self.offer.required_experience <= 0:
            return 100.0

        if self.extractor.year_experience >= self.offer.required_experience:
            return 100.0

        return (self.extractor.year_experience / self.offer.required_experience) * 100.0

    def _score_skills(self) -> float:
        """
            Score the candidate skills comparing to the offer required skills

            Rule:
            Naïve approach by list intersection, considering that all skills are equal
        """
        if not self.offer.required_skills:
            return 100.0

        candidate_skills = {skill.lower() for skill in self.extractor.skills}
        required_skills = {skill.strip().lower() for skill in self.offer.required_skills.split(',')}

        logger.info(f'Candidate skills: {candidate_skills}')
        logger.info(f'Required skills: {required_skills}')

        matches = required_skills.intersection(candidate_skills)

        return 0 if not candidate_skills else (len(matches) / len(candidate_skills)) * 100.0

    def _score_diploma(self) -> float:
        """
            Score the candidate diploma comparing to the offer required diploma
            Rule:
            - Use rank to determine the diploma score PhD=8, Master/Engineer=5, Bachelor=3, BTS/DUT=2, High School Diploma=1
            - 100% if greater or equal to required diploma
            - Rule of 3 if lest than required diploma
        """

        required_diploma_ranking = self.offer.required_diploma_ranking if self.offer.required_diploma_ranking else 0
        if self.extractor.diploma_ranking >= required_diploma_ranking:
            return 100.0

        return (self.extractor.diploma_ranking / self.offer.required_diploma_ranking) * 100.0

    def compute_deterministic_score(self):
        experience_score = self._score_experience()
        skill_score = self._score_skills()
        diploma_score = self._score_diploma()

        self.deterministic_score = {
            'experience_score': experience_score,
            'skill_score': skill_score,
            'diploma_score': diploma_score
        }
        logger.info(f'Computed deterministic score: {self.deterministic_score}')

    def compute_score(self) -> Tuple[float, Dict]:
        """
            Compute final score on the candidate by using the deterministic and the LLM power
        """

        self.compute_deterministic_score()

        if not self.llm:
            # Considering that there is no llm has been charged
            return 0.0, {}

        structured_llm = self.llm.with_structured_output(ScoringData)

        prompt = (
            """
          ### ROLE
You are a Technical Recruitment Expert (Senior Talent Acquisition). Your role is to audit the raw scores generated by an algorithm and add human and semantic nuance to produce the final matching score.

### INPUT DATA
1. JOB CRITERIA: {job_requirements}
2. DATA EXTRACTED FROM THE CV: {candidate_data}
3. DETERMINISTIC SCORES: {deterministic_scores} (Based on strict matching)

### ADJUSTMENT INSTRUCTIONS
- **Experience**: 
  - **CRITICAL**: Only count experience in the SAME DOMAIN as the job offer. Experience in unrelated fields (e.g., healthcare experience for a software engineering role, or finance experience for a marketing role) should NOT contribute to the experience score.
  - Within the relevant domain: If the candidate has fewer years of experience than required but has worked for prestigious companies or on identical technologies, slightly increase the score. 
  - If the candidate has more years of relevant experience than required, cap the score at 100 but mention it as a strength.
  - **Example**: 8 years in healthcare = 0 relevant experience for a software engineering position. Only software engineering experience counts.
  
- **Skills**: Identify synonyms (e.g., 'React' vs. 'ReactJS') or related technologies that the deterministic algorithm may have missed and adjust the score accordingly.

- **Degree**: Assess the relevance of the field of study to the position. A degree in an unrelated field should be scored lower even if the level matches.

### ADDITIONAL CALCULATIONS
- **Language Score (0-100):** Based on the requirements of the job offer (e.g., fluent English) and even the language of the CV.
- **Job Fit (0-100):** Assesses whether past tasks match the job description. Only consider tasks and roles within the same domain as the job offer.

### DOMAIN RELEVANCE VALIDATION
Before scoring experience:
1. Identify the primary domain/industry of the job offer (e.g., Software Engineering, Healthcare, Finance, Marketing, Sales, etc.)
2. For each experience entry in the CV, determine if it belongs to the same domain
3. Exclude or heavily penalize experience from unrelated domains
4. Clearly state in your comments which experiences were considered relevant and which were excluded

### CRITERIA FOR STRENGTHS:
- Years of **RELEVANT** experience (in the same domain) > Required.
- Degree > Required level or in a field relevant/prestigious for the position.
- Relevant certifications **in the job domain**.
- Strong fit between past assignments and future position **within the same domain**.
- Any other relevant insights you found

### WEIGHTS
That are the weights used for the final computation score:
{weights}

### FINAL TASK
Analyze the data and provide the scores and review. 
You must strictly follow the provided output schema for the final JSON response.
Make sure to explain your adjustment in the `score_comments`, especially which experiences were counted as relevant and which were excluded.
Make sure to explain your reasoning in the review section, particularly regarding domain alignment.
            """
        )

        job_requirements = self.offer.to_dict()
        candidate_data = self.extractor.to_dict()

        logger.info('Computing the final score...')
        result = structured_llm.invoke(prompt.format(
            job_requirements=job_requirements,
            candidate_data=candidate_data,
            deterministic_scores=self.deterministic_score,
            weights=self.weights,
        ))
        results = result.dict()
        global_score = self.weights['experience'] * results.get('experience') + self.weights['skills'] * results.get(
            'skills') + self.weights['education'] * results.get('education') + self.weights['languages'] * results.get(
            'languages') + self.weights['job_fit'] * results['job_fit']

        logger.info(f'Computation completed with the result: {global_score}/100')
        logger.info(f'See details below:\n {results}')

        return global_score, results
