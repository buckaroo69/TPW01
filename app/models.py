from django.db import models
from django.contrib.auth.models import User
from django.core.validators import *
# Create your models here.
from django.db.models import CASCADE


class Book(models.Model):
    title = models.CharField(max_length=150)
    author = models.ForeignKey(User, on_delete=CASCADE)
    reviewcount = models.IntegerField() #always compute score via these I guess
    scoretotal = models.BigIntegerField()


class Review(models.Model):
    class Meta:
        unique_together = (('author', 'novel'),)

    author = models.ForeignKey(User)
    novel = models.ForeignKey(Book, on_delete=CASCADE)
    rating = models.IntegerField(default=100, validators=[MinValueValidator(0), MaxValueValidator(100)])
    text = models.CharField(max_length=5000)


class Chapter(models.Model):
    title = models.CharField(max_length=150)
    author = models.ForeignKey(User)
    text = models.CharField()   #TODO: CONSIDER IMPORTING RICH TEXT FIELDS
    novel = models.OneToOneField(Book, on_delete=CASCADE)


class Comment(models.Model):
    class Meta:
        unique_together = (('author', 'chapter'),)

    author = models.ForeignKey(User)
    chapter = models.ForeignKey(Chapter, on_delete=CASCADE)
    content = models.CharField(max_length=1000)
    parent = models.ForeignKey("self", default=None, null=True)

