from django.shortcuts import render
def index(request):
    # return render(request, 'login.html')
    return render(request, 'register.html')