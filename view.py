from django.http import HttpResponse

def view(request):
    '''返回视图'''
    return HttpResponse("ok")
