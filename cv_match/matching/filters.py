import django_filters

from matching.models import CVMatching


class MatchingScoreFilter(django_filters.FilterSet):
    min_score = django_filters.NumberFilter(field_name='score', lookup_expr='gte')

    class Meta:
        model = CVMatching
        fields = ['min_score']
