from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from rango.models import Category, Page, UserProfile
from rango.forms import CategoryForm, PageForm, UserForm, UserProfileForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from datetime import datetime
from rango.bing_search import run_query

def index(request):
    context = RequestContext(request)
    page_list = Page.objects.order_by('-views')[:5]
    context_dict = {'pages' : page_list, 'category_list' : get_category_list()}

    if request.session.get('last_visit'):
        last_visit_time = request.session.get('last_visit')
        visits = request.session.get('visits', 0)

        if (datetime.now() - datetime.strptime(last_visit_time[:-7], "%Y-%m-%d %H:%M:%S")).days > 0:
            request.session['visits'] = visits + 1
            request.session['last_visit'] = str(datetime.now())
    else:
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = 1

    return render_to_response('rango/index.html', context_dict, context)


def about(request):
    context = RequestContext(request)
    if request.session.get('visits'):
        count = request.session.get('visits')
    else:
        count = 0;
    context_dict = {'visits' : count, 'category_list' : get_category_list()}
    return render_to_response('rango/about.html', context_dict, context)
    

def category(request, category_name_url):
    context = RequestContext(request)
    category_name = decode_url(category_name_url)
    context_dict = {'category_name' : category_name, 
                    'category_name_url' : category_name_url,
                    'category_list' : get_category_list()}

    result_list = []
    if request.method == "POST":
        query = request.POST['query'].strip()
        if query:
            result_list = run_query(query)
    context_dict['result_list'] = result_list

    try:
        category = Category.objects.get(name=category_name)
        pages = Page.objects.filter(category=category)
        context_dict['pages'] = pages
        context_dict['category'] = category
    except Category.DoesNotExist:
        pass

    return render_to_response('rango/category.html', context_dict, context)


def add_category(request):
    context = RequestContext(request)

    if request.method == 'POST':
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save(commit=True)
            return index(request)
        else:
            print form.errors
    else:
        form = CategoryForm()
    context_dict = {'form' : form, 'category_list' : get_category_list()}

    return render_to_response('rango/add_category.html', context_dict, context)

def add_page(request, category_name_url):
    context = RequestContext(request)

    category_name = decode_url(category_name_url)
    if request.method == 'POST':
        form = PageForm(request.POST)

        if form.is_valid():
            page = form.save(commit=False)

            try:
                cat = Category.objects.get(name=category_name)
                page.category = cat
            except Category.DoesNotExist:
                return render_to_response('rango/add_category.html', {}, context)

            page.views = 0
            page.save()

            return category(request, category_name_url)
        else:
            print form.errors
    else:
        form = PageForm()

    context_dict = {'category_name_url' : category_name_url,
                    'category_name' : category_name, 'form' : form,
                    'category_list' : get_category_list()}

    return render_to_response('rango/add_page.html', context_dict, context)

def register(request):
    context = RequestContext(request)
    registered = False

    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']
            profile.save()

            registered = True
        else:
            print user_form.errors, profile_form.errors
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    context_dict = {'user_form' : user_form, 'profile_form' : profile_form,
                    'registered' : registered, 'category_list' : get_category_list()}

    return render_to_response('rango/register.html', context_dict, context)

def user_login(request):
    context = RequestContext(request)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect('/rango/')
            else:
                return HttpResponse("Your Rango account has been disabled.")
        else:
            print "Invalid login details: {0}, {1}".format(username, password)
            return HttpResponse("Username or password is invalid.")

    else:
        context_dict = {'category_list' : get_category_list()}
        return render_to_response('rango/login.html', context_dict, context)

@login_required
def profile(request):
    context = RequestContext(request)
    user = request.user
    user_profile = UserProfile.objects.get(user=user)
    context_dict = {'username' : user.username, 'email' : user.email, 
                    'website' : user_profile.website, 'picture' : user_profile.picture,
                    'category_list' : get_category_list()}
    return render_to_response('rango/profile.html', context_dict, context)

def track_url(request):
    context = RequestContext(request)

    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            page = Page.objects.get(id=page_id)
            page.views += 1
            page.save()
            return HttpResponseRedirect(page.url)
    return render_to_response('rango/', {}, context)

@login_required
def restricted(request):
    context = RequestContext(request)
    context_dict = {'message' : "Since you're logged in, you can see this text!",
                    'category_list' : get_category_list()}
    return render_to_response('rango/restricted.html', context_dict, context)

@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect('/rango/')


def encode_url(category):
    category.url = category.name.replace(' ', '_')

def decode_url(category):
    return category.replace('_', ' ')

def get_category_list():
    category_list = Category.objects.all()
    for category in category_list:
        encode_url(category)
    return category_list

