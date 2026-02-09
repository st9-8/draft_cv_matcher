import logging
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field

from django.conf import settings

from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.chat_models import ChatOllama

import mammoth
import pdfplumber
from traceback_with_variables import format_exc

from matching.models import CV

logger = logging.getLogger(__name__)


class CVData(BaseModel):
    name: str = Field(None, description="Candidate name")
    website: str = Field(None, description="Candidate website")
    phone_number: str = Field(None, description="Candidate phone number")
    email: str = Field(None, description="Candidate email")
    description: str = Field(None, description="Candidate profile description")
    skills: List[str] = Field(default_factory=list, description='Candidate technical and soft skills')
    diploma: str = Field(None, description="Candidate highest diploma (e.g: Master, Bachelor, PhD")
    diploma_ranking: int = Field(default=0,
                                 description='Candidate highest diploma rank. PhD=8, Master/Engineer=5, Bachelor=3, BTS/DUT=2, High School Diploma=1')
    year_experience: int = Field(default=0, description="Total cumulated experience years")
    experiences: List[str] = Field(None,
                                   description="Candidate experience in each company (role, company name, tasks realized, duration/period, contract type, work type")
    languages: List[str] = Field(default_factory=list, description="Candidate languages")
    certifications: List[str] = Field(default_factory=list, description="Candidate certifications list")


class Extractor(object):
    """
        Extractor class
    """

    def __init__(self, cv: CV):
        self.cv: CV = cv
        self.name: Optional[str] = None
        self.website: Optional[str] = None
        self.phone_number: Optional[str] = None
        self.email: Optional[str] = None
        self.description: Optional[str] = None
        self.skills: List = []
        self.diploma: Optional[str] = None
        self.diploma_ranking: Optional[int] = None
        self.year_experience: Optional[int] = None
        self.experiences: List[str] = []
        self.languages: List[str] = []
        self.certifications: List[str] = []
        self.raw_text: Optional[str] = None

    def extract_raw(self) -> Optional[str]:
        """
            This function returns the raw text from the CV
        """
        cv_path = Path(self.cv.file.path)
        raw_text = ''

        if cv_path.suffix in ['.docx', '.doc', '.DOCX', '.DOC']:
            raw_text = self._extract_raw_docx()
        elif cv_path.suffix in ['.pdf', '.PDF']:
            raw_text = self._extract_raw_pdf()
        else:
            logger.warning(f'Unsupported file type: {cv_path.suffix}')
        if not raw_text:
            raise ValueError(f'Sorry we were unable to extract anything from this CV')

        return raw_text

    def _extract_raw_pdf(self) -> str:
        """
            This function returns the raw text from a PDF CV
        """
        with pdfplumber.open(self.cv.file.path) as pdf:
            raw_text = []

            for page in pdf.pages:
                if page.extract_text():
                    raw_text.append(page.extract_text())
                else:
                    logger.warning(f'Cannot extract text from PDF page {page.page_number}')

        return '\n'.join(raw_text).strip()

    def _extract_raw_docx(self) -> str:
        """
            This function returns the raw text from a Word CV
        """
        with open(self.cv.file.path, 'rb') as docx_file:
            result = mammoth.extract_raw_text(docx_file)
            raw_text = result.value.strip()

        logger.info(f'Raw text from Docx ({len(raw_text)} chars): {raw_text[:200]}...')

        return raw_text

    def semantic_extract(self):
        """
            The aim of this function is use an LLM to extract structured data from raw text

            - name: Optional[str] = None
            - website: Optional[str] = None
            - phone_number: Optional[str] = None
            - email: Optional[str] = None
            - description: Optional[str] = None
            - skills: List[str] = []
            - diploma: Optional[str] = None
            - certifications: List[str] = None
            - year_experience: Optional[int] = None
            - experiences: List[str] = None
            - languages: Optional[str] = None
        """

        try:
            if settings.EXTRACTION_MODEL_PROVIDER == 'openai':
                llm = ChatOpenAI(model=settings.EXTRACTION_MODEL, temperature=0)

            elif settings.EXTRACTION_MODEL_PROVIDER == 'anthropic':
                llm = ChatAnthropic(model=settings.EXTRACTION_MODEL, temperature=0)

            elif settings.EXTRACTION_MODEL_PROVIDER == 'ollama':
                llm = ChatOllama(model=settings.EXTRACTION_MODEL, temperature=0)

            else:
                logger.warning(f'Unsupported model provider: {settings.EXTRACTION_MODEL_PROVIDER}')
                return

            structured_llm = llm.with_structured_output(CVData)

            prompt = (
                """
You are an expert in recruitment (ATS).
Extract structured information from the plain text of the CV below.

IMPORTANT: Extract all information in the SAME LANGUAGE as the CV (if CV is in French, extract in French; if in English, extract in English).

For `year_experience`, calculate the total duration between the first experience and today.

For `experiences`, extract:
- Role, company name, duration, period, contract type, work type
- A concise summary (2-3 sentences maximum, ~50 words) highlighting the most impactful contributions and key technologies used. Focus on outcomes and scope rather than listing every task.

Example of good summary:
"Led backend development for B2B payment solutions serving 50+ Swedish e-commerce clients. Architected Payero.se integration with Swish mobile payments and accounting APIs (Fortnox, Visma). Built AI-powered customer support automation using Langchain and deployed microservices with Docker."

MANDATORY: Always return JSON format only, without any text or comments around.

Raw CV text: 
{raw_text}
"""

            )

            self.raw_text = self.extract_raw()
            result: CVData = structured_llm.invoke(prompt.format(raw_text=self.raw_text))

            self.name = result.name
            self.website = result.website
            self.phone_number = result.phone_number
            self.email = result.email
            self.description = result.description
            self.skills = result.skills
            self.diploma = result.diploma
            self.diploma_ranking = result.diploma_ranking
            self.year_experience = result.year_experience
            self.experiences = result.experiences
            self.languages = result.languages

            self.save()

        except Exception as e:
            logger.error(format_exc(e))
            raise ValueError(e) from e

    def to_dict(self):
        return {
            'description': self.description,
            'skills': ', '.join(self.skills),
            'diploma': self.diploma,
            'year_experience': self.year_experience,
            'experiences': ', '.join(self.experiences),
            'languages': ', '.join(self.languages),
            'certifications': ', '.join(self.certifications)
        }

    def save(self):
        """
            Save extracted CV data
        """
        self.cv.name = self.name
        self.cv.website = self.website
        self.cv.phone_number = self.phone_number
        self.cv.email = self.email
        self.cv.description = self.description
        self.cv.skills = ', '.join(self.skills)
        self.cv.diploma = self.diploma
        self.cv.diploma_ranking = self.diploma_ranking
        self.cv.year_experience = self.year_experience
        self.cv.experiences = self.experiences
        self.cv.languages = ', '.join(self.languages)
        self.cv.certifications = self.certifications
        self.cv.raw_text = self.raw_text

        self.cv.save()
