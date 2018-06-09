from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter

from test_samples.sample.sampleapp import views, views_author, views_review

router = DefaultRouter()
router.register('article', views.ArticleViewSet)
router.register('article_limit_fields', views.ArticleViewSetLimitFields)
router.register('author', views_author.AuthorViewSet)
router.register('dynmixin_article', views_author.ArticleDynMixinViewSet)
router.register('dynmixin_author', views_author.AuthorDynMixinViewSet)
router.register('review', views_review.ReviewViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
