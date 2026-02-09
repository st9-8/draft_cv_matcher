import logging

from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser, JSONParser
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema

from traceback_with_variables import format_exc

from matching.filters import MatchingScoreFilter
from matching.models import CV
from matching.models import JobOffer
from matching.serializers import CVMatchingSerializer
from matching.serializers import CVScoreSerializer
from matching.serializers import CVSerializer
from matching.serializers import JobOfferSerializer

logger = logging.getLogger(__name__)


class LoggingModelViewSet(viewsets.ModelViewSet):
    """
        Base ViewSet that centralizes exception logging.
    """

    def handle_exception(self, exc):
        logger.error(format_exc(exc))
        return super().handle_exception(exc)


class JobOfferViewSet(LoggingModelViewSet):
    queryset = JobOffer.objects.all().order_by('-created_at')
    serializer_class = JobOfferSerializer
    http_method_names = ['get', 'post', 'patch', 'delete']

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='min_score',
                location=OpenApiParameter.QUERY,
                required=False,
                type=OpenApiTypes.FLOAT,
                description='Minimum score (0-100) a CV must have to be returned.',
            )
        ],
        responses=CVMatchingSerializer(many=True),
    )
    @action(detail=True, methods=['get'], url_path='matched_cvs')
    def matched_cvs(self, request, pk=None):
        job_offer = self.get_object()
        base_queryset = job_offer.matchings.select_related('cv').order_by('-score')
        filterset = MatchingScoreFilter(data=request.query_params, queryset=base_queryset)

        if not filterset.is_valid():
            raise ValidationError(filterset.errors)

        queryset = filterset.qs

        page = self.paginate_queryset(queryset)
        serializer = CVMatchingSerializer(page or queryset, many=True)

        if page is not None:
            return self.get_paginated_response(serializer.data)

        return Response(serializer.data, status=status.HTTP_200_OK)


class CVViewSet(LoggingModelViewSet):
    queryset = CV.objects.all().order_by('-uploaded_at')
    serializer_class = CVSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    http_method_names = ['get', 'post', 'patch', 'delete']

    @action(detail=True, methods=['post'], serializer_class=CVScoreSerializer, url_path='score_job_offer')
    def score_job_offer(self, request, pk=None):
        cv = self.get_object()
        serializer = CVScoreSerializer(data=request.data, context={'cv': cv})
        serializer.is_valid(raise_exception=True)

        result = serializer.save()
        return Response(result, status=status.HTTP_200_OK)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='min_score',
                location=OpenApiParameter.QUERY,
                required=False,
                type=OpenApiTypes.FLOAT,
                description='Minimum score (0-100) a job offer must have to be returned.',
            )
        ],
        responses=CVMatchingSerializer(many=True),
    )
    @action(detail=True, methods=['get'], url_path='matched-job-offers')
    def matched_job_offers(self, request, pk=None):
        cv = self.get_object()
        base_queryset = cv.matchings.select_related('job_offer').order_by('-score')
        filterset = MatchingScoreFilter(data=request.query_params, queryset=base_queryset)

        if not filterset.is_valid():
            raise ValidationError(filterset.errors)

        queryset = filterset.qs

        page = self.paginate_queryset(queryset)
        serializer = CVMatchingSerializer(page or queryset, many=True)

        if page is not None:
            return self.get_paginated_response(serializer.data)

        return Response(serializer.data, status=status.HTTP_200_OK)
