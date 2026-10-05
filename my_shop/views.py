import os
from django.conf import settings
from django.http import HttpResponse

def yandex_verify(request):
    file_path = os.path.join(settings.BASE_DIR, 'zbWxDvr6uVru67mynf3g59z.txt')
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return HttpResponse(f.read(), content_type='text/plain')
    except FileNotFoundError:
        return HttpResponse('File not found', status=404)