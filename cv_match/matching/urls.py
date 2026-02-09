from rest_framework.routers import DefaultRouter

from matching.views import CVViewSet
from matching.views import JobOfferViewSet

router = DefaultRouter()
router.register(r'job_offers', JobOfferViewSet, basename='job_offers')
router.register(r'cvs', CVViewSet, basename='cvs')

urlpatterns = router.urls
