import os
import shutil
import sys


def save_media():
    """Сохраняет медиа файлы в безопасное место"""
    source = os.path.join(os.path.dirname(__file__), 'media')
    target = os.path.expanduser('~/media_backup')

    if os.path.exists(source):
        shutil.copytree(source, target, dirs_exist_ok=True)
        print(f"✅ Медиа сохранены в {target}")
    else:
        print("❌ Папка media не найдена")


if __name__ == '__main__':
    save_media()