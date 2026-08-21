import os
import sys
import django
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from pathlib import Path

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_shop.settings')

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

django.setup()


def migrate_media_to_s3():
    """Переносит медиа файлы из локальной папки в S3"""
    from apps.products.models import Product, ProductImage, ProductVideo
    from apps.accounts.models import CustomUser

    success_count = 0
    error_count = 0

    print("🚀 Начинаем миграцию медиа в S3...")
    print(f"📁 Используется хранилище: {default_storage.__class__.__name__}")

    # 1. Переносим главные изображения товаров
    print("\n📸 Перенос главных изображений товаров...")
    for product in Product.objects.all():
        if product.image and product.image.name:
            try:
                # Проверяем, есть ли файл в локальном хранилище
                local_path = os.path.join(settings.MEDIA_ROOT, product.image.name)
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        default_storage.save(product.image.name, ContentFile(f.read()))
                    success_count += 1
                    print(f"  ✅ {product.image.name}")
                else:
                    print(f"  ⚠️ Файл не найден: {local_path}")
            except Exception as e:
                error_count += 1
                print(f"  ❌ Ошибка: {product.image.name} - {str(e)}")

    # 2. Переносим дополнительные изображения
    print("\n📸 Перенос дополнительных изображений...")
    for img in ProductImage.objects.all():
        if img.image and img.image.name:
            try:
                local_path = os.path.join(settings.MEDIA_ROOT, img.image.name)
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        default_storage.save(img.image.name, ContentFile(f.read()))
                    success_count += 1
                    print(f"  ✅ {img.image.name}")
                else:
                    print(f"  ⚠️ Файл не найден: {local_path}")
            except Exception as e:
                error_count += 1
                print(f"  ❌ Ошибка: {img.image.name} - {str(e)}")

    # 3. Переносим видео
    print("\n🎬 Перенос видео...")
    for video in ProductVideo.objects.all():
        if video.video and video.video.name:
            try:
                local_path = os.path.join(settings.MEDIA_ROOT, video.video.name)
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        default_storage.save(video.video.name, ContentFile(f.read()))
                    success_count += 1
                    print(f"  ✅ {video.video.name}")
                else:
                    print(f"  ⚠️ Файл не найден: {local_path}")
            except Exception as e:
                error_count += 1
                print(f"  ❌ Ошибка: {video.video.name} - {str(e)}")

    # 4. Переносим миниатюры видео
    print("\n🖼️ Перенос миниатюр видео...")
    for video in ProductVideo.objects.all():
        if video.thumbnail and video.thumbnail.name:
            try:
                local_path = os.path.join(settings.MEDIA_ROOT, video.thumbnail.name)
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        default_storage.save(video.thumbnail.name, ContentFile(f.read()))
                    success_count += 1
                    print(f"  ✅ {video.thumbnail.name}")
                else:
                    print(f"  ⚠️ Файл не найден: {local_path}")
            except Exception as e:
                error_count += 1
                print(f"  ❌ Ошибка: {video.thumbnail.name} - {str(e)}")

    # 5. Переносим аватары пользователей
    print("\n👤 Перенос аватаров пользователей...")
    for user in CustomUser.objects.all():
        if hasattr(user, 'avatar') and user.avatar and user.avatar.name:
            try:
                local_path = os.path.join(settings.MEDIA_ROOT, user.avatar.name)
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        default_storage.save(user.avatar.name, ContentFile(f.read()))
                    success_count += 1
                    print(f"  ✅ {user.avatar.name}")
                else:
                    print(f"  ⚠️ Файл не найден: {local_path}")
            except Exception as e:
                error_count += 1
                print(f"  ❌ Ошибка: {user.avatar.name} - {str(e)}")

    print(f"\n📊 Результат:")
    print(f"  ✅ Успешно перенесено: {success_count} файлов")
    print(f"  ❌ Ошибок: {error_count}")
    print("🎉 Миграция завершена!")


if __name__ == '__main__':
    migrate_media_to_s3()