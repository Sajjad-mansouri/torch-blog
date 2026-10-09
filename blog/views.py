# Create your views here.
from django.views.generic import TemplateView


class PostsTemplateView(TemplateView):
    template_name = "blog/posts.html"


class PostDetailView(TemplateView):
    template_name = "blog/post.html"
