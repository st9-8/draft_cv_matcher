from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from matching.enums import WorkType
from matching.enums import ContractType


class JobOffer(models.Model):
    title: models.CharField = models.CharField(max_length=200)
    description: models.TextField = models.TextField()
    required_skills: models.CharField = models.TextField(help_text='Enter a comma-separated list of skills')
    company_name: models.CharField = models.CharField(max_length=200)
    location: models.CharField = models.CharField(max_length=200)
    start_date: models.DateField = models.DateField(blank=True, null=True)
    required_languages: models.CharField = models.CharField(max_length=255,
                                                            help_text='Enter a comma-separated list of languages')
    required_diploma: models.CharField = models.CharField(max_length=255)
    required_diploma_ranking: models.IntegerField = models.IntegerField(blank=True, null=True,
                                                                        help_text='PhD=8, Master/Engineer=5, Bachelor=3, BTS/DUT=2, High School Diploma=1')
    required_experience: models.IntegerField = models.IntegerField(help_text='Number of years of experience')
    contract_type: models.CharField = models.CharField(max_length=255, choices=ContractType.choices)
    work_type: models.CharField = models.CharField(max_length=255, choices=WorkType.choices)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)
    expires_at: models.DateTimeField = models.DateTimeField(blank=True, null=True)
    is_expired: models.BooleanField = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def to_dict(self):
        return {
            'title': self.title,
            'description': self.description,
            'required_skills': self.required_skills,
            'company_name': self.company_name,
            'location': self.location,
            'start_date': self.start_date,
            'required_languages': self.required_languages,
            'required_diploma': self.required_diploma,
            'required_experience': self.required_experience,
            'contract_type': self.contract_type,
            'work_type': self.work_type,
        }

    class Meta:
        verbose_name = 'Job Offer'
        verbose_name_plural = 'Job Offers'


class CV(models.Model):
    # Mandatory fields
    title: models.CharField = models.CharField(max_length=200)
    file: models.FileField = models.FileField(upload_to='cv/')
    uploaded_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    # Extracted fields
    name: models.CharField = models.CharField(max_length=255, help_text='Candidate name', blank=True)
    website: models.CharField = models.CharField(max_length=255, help_text='Candidate website', blank=True)
    phone_number: models.CharField = models.CharField(max_length=255, help_text='Candidate phone number', blank=True)
    email: models.CharField = models.CharField(max_length=255, help_text='Candidate email', blank=True)
    description: models.TextField = models.TextField(blank=True, help_text="Candidate's bio")
    skills: models.TextField = models.TextField(blank=True, help_text="Candidate's skills in comma-separated values")
    diploma: models.TextField = models.TextField(blank=True, help_text="Candidate's diplomas")
    diploma_ranking: models.IntegerField = models.IntegerField(blank=True, null=True)
    certifications: models.JSONField = models.JSONField(blank=True)
    year_experience: models.IntegerField = models.IntegerField(blank=True, null=True)
    experiences: models.JSONField = models.JSONField(blank=True, help_text="Candidate's summarized experiences")
    languages: models.TextField = models.TextField(blank=True, help_text="Candidate's languages")
    raw_text: models.TextField = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'CV'
        verbose_name_plural = 'CVs'


class CVMatching(models.Model):
    job_offer: models.ForeignKey = models.ForeignKey(JobOffer, on_delete=models.CASCADE, related_name='matchings')
    cv: models.ForeignKey = models.ForeignKey(CV, on_delete=models.CASCADE, related_name='matchings')
    evaluated_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    score: models.FloatField = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(100.0)])
    score_description: models.JSONField = models.JSONField()

    def __str__(self):
        return f'{self.cv} scored {self.score} on Job offer {self.job_offer}'

    class Meta:
        verbose_name = 'Matching'
        verbose_name_plural = 'Matchings'
