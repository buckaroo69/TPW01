from django.contrib import admin
from app.models import *
# Register your models here.
admin.site.register(Book)
admin.site.register(Chapter)
admin.site.register(Comment)
admin.site.register(Review)