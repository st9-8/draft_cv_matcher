from django.contrib import admin

from matching.models import CV
from matching.models import JobOffer
from matching.models import CVMatching


@admin.register(JobOffer)
class JobOfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'company_name', 'contract_type', 'work_type', 'location', 'created_at', 'is_expired')
    list_filter = ('contract_type', 'work_type', 'is_expired')
    search_fields = ('title', 'company_name', 'description', 'location')


@admin.register(CV)
class CVAdmin(admin.ModelAdmin):
    list_display = ('title', 'uploaded_at')


@admin.register(CVMatching)
class CVMatchingAdmin(admin.ModelAdmin):
    list_display = ('job_offer', 'cv', 'score', 'evaluated_at')
    list_filter = ('job_offer', 'cv')
