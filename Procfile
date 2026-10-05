web: daphne -b 0.0.0.0 -p 8000 my_shop.asgi:application
worker: celery -A my_shop worker --loglevel=INFO
beat: celery -A my_shop beat --loglevel=INFO
