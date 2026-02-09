import json
import logging

from django.utils import timezone

from rest_framework import serializers

from traceback_with_variables import format_exc

from matching.models import CV
from matching.models import CVMatching
from matching.models import JobOffer
from matching.scorer import GlobalScorer

logger = logging.getLogger(__name__)


class JobOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobOffer
        fields = ['title', 'description', 'required_skills', 'company_name', 'location', 'start_date',
                  'required_languages', 'required_diploma', 'required_diploma_ranking', 'required_experience',
                  'contract_type', 'work_type', 'created_at', 'updated_at', 'expires_at', 'is_expired']


class CVSerializer(serializers.ModelSerializer):
    class Meta:
        model = CV
        fields = ['title', 'file', 'uploaded_at', 'updated_at', 'uploaded_at',
                  'updated_at', 'name', 'website', 'phone_number', 'email', 'description', 'skills', 'diploma',
                  'diploma_ranking', 'certifications', 'year_experience', 'experiences', 'languages', 'raw_text', ]
        read_only_fields = (
            'uploaded_at',
            'updated_at',
            'name',
            'website',
            'phone_number',
            'email',
            'description',
            'skills',
            'diploma',
            'diploma_ranking',
            'certifications',
            'year_experience',
            'experiences',
            'languages',
            'raw_text',
        )


class CVMatchingSerializer(serializers.ModelSerializer):
    job_offer = JobOfferSerializer(read_only=True)
    cv = CVSerializer(read_only=True)
    score_details = serializers.SerializerMethodField()

    class Meta:
        model = CVMatching
        fields = (
            'id',
            'job_offer',
            'cv',
            'score',
            'score_details',
            'score_description',
            'evaluated_at',
        )
        read_only_fields = fields

    def get_score_details(self, obj: CVMatching):
        if not obj.score_description:
            return {}

        try:
            return json.loads(obj.score_description)
        except (TypeError, json.JSONDecodeError):
            return {'raw': obj.score_description}


class CVScoreSerializer(serializers.Serializer):
    job_offer_id = serializers.PrimaryKeyRelatedField(
        source='job_offer',
        queryset=JobOffer.objects.all(),
        help_text='Identifier of the job offer the CV should be matched against',
    )

    def validate(self, attrs):
        cv: CV = self.context['cv']

        if not cv.file:
            raise serializers.ValidationError({'cv': ['CV file not found. Upload a file before scoring.']})

        return attrs

    def save(self, **kwargs):
        job_offer: JobOffer = self.validated_data['job_offer']
        cv: CV = self.context['cv']

        try:
            scorer = GlobalScorer(offer=job_offer, cv=cv)
            score_value, score_details = scorer.compute_score()
        except Exception as exc:
            logger.error(format_exc(exc))
            raise serializers.ValidationError({'non_field_errors': ['Unable to compute score.']}) from exc

        try:
            serialized_details = json.dumps(score_details)
        except (TypeError, ValueError) as exc:
            logger.error(format_exc(exc))
            raise serializers.ValidationError({'non_field_errors': ['Unable to serialize score details.']}) from exc

        evaluation_time = timezone.now()
        matching, _ = CVMatching.objects.update_or_create(
            job_offer=job_offer,
            cv=cv,
            defaults={
                'score': score_value,
                'score_description': serialized_details,
                'evaluated_at': evaluation_time,
            }
        )

        return {
            'matching_id': matching.id,
            'score': matching.score,
            'score_details': score_details,
            'evaluated_at': matching.evaluated_at,
            'job_offer': JobOfferSerializer(job_offer).data,
            'cv': CVSerializer(cv).data,
        }
