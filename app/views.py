from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.shortcuts import render, redirect

from app.commonqueries import *
from app.creationMethods import *
from app.forms import ChapterPostForm, BookCreationForm
from app.models import *


# Create your views here.

#TODO:
# i dont want user stats but that's just cuz they're a pain, we can add them in - not that important (leave for last)


# DONE ON SERVER END
# user profile page viewing and changing all reviews in another tab maybe? - may be too much for this project (leave for last)
# load latest chapters and top rated fics onto frontpage -> NEW IDEA: HOT CAN BE WHATEVER HAS GOTTEN MOST RATING IN LAST X HOURS
# CHAPTER READING PAGE INCLUDING COMMENTS, CONSIDER USING PAGING FOR COMMENTS JUST 'CAUSE (no clue how to make hierarchical comments work in django templating btw)
# top rated/ hot pages / new pages -> just needs the view I think
# make a login/sign in page AFTER we learn how that stuff works
# allow any user to save books for easy access in a following page -> bookmarked is a thing, just need to get a form or JS call going browser side
# user profile page allowing new-book creation
# book page allowing anyone to select chapters, allowing normal users to review and allowing the author to move into the chapter creation menu
# REST for making/deleting/editing (description and title only) a book
# REST for adding/removing/editing chapters

# HOME PAGE
def index(request):
    data = {'newchaps': Chapter.objects.order_by("-release").select_related()[:10], 'toprated': bookbyrating(total=10),
            'rising': bookrisingpop(total=10)}
    return render(request, "index.html", data)


def bookpage(request, pk):
    data = {'book': Book.objects.select_related().get(pk=pk), 'lastread': 0, 'isauthor': False}
    data['chapters'] = Chapter.objects.only("title", "number", "release").filter(novel=data['book'])
    data['reviews'] = Review.objects.filter(novel=data['book']).select_related('author')
    if request.user.is_authenticated:
        possiblereview = Review.objects.filter(author=request.user, novel_id=pk)
        data['isauthor'] = request.user == data['book'].author
        if possiblereview.exists():
            data['reviewform'] = ReviewForm(possiblereview.get())
        else:
            data['reviewform'] = ReviewForm()  # do not render this if author or nonauth'd
        lastread = LastRead.objects.get(book_id=pk, author=request.user)
        if lastread is not None:
            data['lastread'] = lastread.chapter
            data['bookmarked'] = Bookmarked.objects.filter(author=request.user, book_id=pk).exists()
    else:
        data['bookmarked'] = False
    return render(request, 'book.html', data)


def topRated(request, page):
    data = {'sorttype': 'Books By Rating', 'books': bookbyrating(page)}
    return render(request, 'listing.html', data)


def popularBooks(request, page):
    data = {'sorttype': 'Rising Books', 'books': bookrisingpop(page)}
    return render(request, 'listing.html', data)


def newBooks(request, page):
    data = {'sorttype': 'New Books', 'books': bookbynew(page)}
    return render(request, 'listing.html', data)


def userpage(request):
    if not request.user.is_authenticated:
        return HttpResponse('uh oh stinky', 403)
    data = {'user': request.user, 'books': bookbyauthor(request.user), 'reviews': reviewbyuser(request.user), }
    return render(request, 'user.html', data)


def chapterpage(request, pk, page):
    data = {'chapter': Chapter.objects.get(pk=pk).select_related(), 'comments': commentspage(pk, page)}
    return render(request, 'chapter.html', data)


def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            return redirect('/')
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form})


def bookmark(request):
    if 'bookid' not in request.POST:
        return redirect("/")
    if request.user.is_authenticated:
        bookmarkSWITCH(request, request.POST['bookid'])
    return redirect(f"book/{request.POST['bookid']}/")


def createReview(request):
    if 'novel' not in request.POST:
        return redirect("/")
    if request.user.is_authenticated:
        reviewPOST(request)
    return redirect(f"book/{request.POST['novel']}/")


def chaptereditor(request,book,chapter):
    novel = Book.objects.get(pk=book)
    if not (request.user.is_authenticated and novel.author == request.user):
        return HttpResponse("very stinky", 403)
    if chapter == "new":
        form = ChapterPostForm()
        form.novel = novel
        chid = 0
    else:
        chap = Chapter.objects.get(novel_id=book,number=int(chapter))
        chid = chap.id
        form = ChapterPostForm(instance=chap)
        form.novel = novel
    data = {'book': novel, 'form':form ,'chapter_id':chid}
    return render(request,"chaptereditor.html",data)

def bookEditor(request,book):  # book=0 if new?
    if not request.user.is_authenticated:
        return HttpResponse('sus',403)
    novel = Book.objects.filter(pk=book)
    if novel.exists():
        novel = novel.get()
        if novel.author != request.user:
            return HttpResponse('sus', 403)
    else:
        novel = Book(author=request.user)
    form = BookCreationForm(instance=novel)
    return render(request,"bookeditor.html",{'bookid':book, 'form':form})


def deletebook(request,book):
    novel = Book.objects.filter(pk=book)
    if not request.user.is_authenticated or not (request.user.is_staff or request.user == novel.author):
        return HttpResponse('get out',403)
    novel.delete()
    return redirect('/')


def submitbook(request,book):
    if not request.user.is_authenticated:
        return HttpResponse('get out', 403)
    novel = Book.objects.filter(pk=book)
    if not novel.exists():
        novel = Book(author=request.user)
    else:
        novel = novel.get()
    if request.user != novel.author:
        return HttpResponse('get out', 403)
    form = BookCreationForm(request.post)
    if form.is_valid():
        novel.title = form.cleaned_data['title']
        novel.description = form.cleaned_data['description']
        novel.save()
        return redirect(f'book/{book}')
    else:
        return render(request,"bookeditor.html",{'bookid':book, 'form':form})


def submitchapter(request,chapterid):
    if not request.user.is_authenticated or 'novel' not in request.POST:
        return HttpResponse('get out', 403)
    chapter = Chapter.objects.filter(pk=chapterid)
    if chapter.exists():
        chapter = chapter.get()
        chid = chapter.id
    else:
        chapter = Chapter()
        chid = 0
    form = ChapterPostForm(request.POST)
    if form.is_valid():
        if Book.objects.get(pk=form.cleaned_data['novel']).author != request.user:
            return HttpResponse('get out', 403)
        chapter.novel = form.cleaned_data['novel']
        chapter.title = form.cleaned_data['title']
        chapter.text = form.cleaned_data['text']
        chaptersubmittransaction(chid,chapter)
        return redirect(f'books/{form.cleaned_data["novel"]}')
    else:
        data = {'chapter_id':chid, 'book': Book.objects.get(pk=request.post['novel']), 'form': form}
        return render(request, "chaptereditor.html", data)

@transaction.atomic
def chaptersubmittransaction(chid,chapter):
    if not chid:  # new chapter
        chapter.novel.chapters += 1
        chapter.number = chapter.novel.chapters
        chapter.novel.save()
    chapter.save()

def deletechapter(request,chapter):
    if not request.user.is_authenticated:
        return HttpResponse('get out', 403)
    chapter = Chapter.objects.filter(pk=chapter)
    if chapter.exists():
        chapter = chapter.get()
        if request.user.is_staff or chapter.novel.author == request.user:
            nv = chapter.novel
            chapterdeletetransaction(chapter)

            return redirect(f'books/{nv}')
        return HttpResponse("No permission",403)
    else:
        return HttpResponse("Not Found", 404)

@transaction.atomic
def chapterdeletetransaction(chapter):
    Chapter.objects.filter(novel=chapter.novel,number__gt=chapter.number).update(number=F('number')-1)
    chapter.novel.chapters -= 1
    chapter.novel.save()
    chapter.delete()