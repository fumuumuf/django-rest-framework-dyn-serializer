from rest_framework import viewsets
# Create your views here.
from rest_framework.serializers import ModelSerializer

from rest_framework_dyn_serializer import DynModelSerializer, DynSerializerMixin
from test_samples.sample.sampleapp.models import Article, Author, Review


class ReviewDynSerializer(DynModelSerializer):
    class Meta:
        model = Review
        fields_param = 'review_fields'
        fields = ['id', 'summary', 'content', 'stars', 'article']
        limit_fields = True


class ArticleDynSerializer(DynModelSerializer):
    review = ReviewDynSerializer(many=True, source='reviews')

    class Meta:
        model = Article
        fields_param = 'article_fields'
        fields = ['id', 'title', 'created', 'updated', 'content', 'review']
        limit_fields = True


class AuthorDynSerializer(DynModelSerializer):
    article = ArticleDynSerializer(many=True, source='articles')

    class Meta:
        model = Author
        fields_param = 'author_fields'
        fields = ['id', 'name', 'birth_date', 'article']
        limit_fields = True


class ArticleDynMixinSerializer(DynSerializerMixin, ModelSerializer):
    review = ReviewDynSerializer(many=True, source='reviews')

    class Meta:
        model = Article
        fields = ['id', 'title', 'created', 'updated', 'content', 'review']


class AuthorDynMixinSerializer(DynSerializerMixin, ModelSerializer):
    article = ArticleDynMixinSerializer(many=True, source='articles')

    class Meta:
        model = Author
        fields = ['id', 'name', 'birth_date', 'article']


class AuthorViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuthorDynSerializer
    queryset = Author.objects.all().order_by('id')


class ArticleDynMixinViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ArticleDynMixinSerializer
    queryset = Article.objects.all().order_by('id')


class AuthorDynMixinViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuthorDynMixinSerializer
    queryset = Author.objects.all().order_by('id')
