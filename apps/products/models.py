import os
import subprocess
from django.db import models
from django.core.files import File
from django.urls import reverse
from django.conf import settings


class Category(models.Model):
    name = models.CharField('Название категории', max_length=100)
    slug = models.SlugField(unique=True)
    image = models.ImageField('Изображение категории', upload_to='categories/', blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:product_list_by_category', args=[self.slug])


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField('Описание')
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    image = models.ImageField('Главное фото', upload_to='products/', blank=True, null=True)
    available = models.BooleanField('В наличии', default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # Артикул
    sku = models.CharField('Артикул', max_length=50, blank=True, null=True, unique=True)

    # Характеристики
    material = models.CharField('Материал', max_length=200, blank=True, null=True)
    composition = models.CharField('Состав материала', max_length=300, blank=True, null=True)
    size_on_model = models.CharField('Размер на модели', max_length=20, blank=True, null=True)
    height_on_model = models.CharField('Рост на модели', max_length=20, blank=True, null=True)
    model_params = models.CharField('Параметры модели (ОГ-ОТ-ОБ)', max_length=50, blank=True, null=True)
    color = models.CharField('Цвет', max_length=100, blank=True, null=True)
    russian_size = models.CharField('Российский размер', max_length=20, blank=True, null=True)
    country = models.CharField('Страна-изготовитель', max_length=100, blank=True, null=True)
    lining_material = models.CharField('Материал подкладки', max_length=200, blank=True, null=True)
    fastener_type = models.CharField('Вид застежки', max_length=100, blank=True, null=True)
    sleeve = models.CharField('Рукав', max_length=100, blank=True, null=True)
    set_composition = models.CharField('Состав комплекта', max_length=200, blank=True, null=True)
    care_instructions = models.TextField('Уход за вещами', blank=True, null=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ('-created',)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('products:product_detail', args=[self.category.slug, self.slug])

    def get_images(self):
        return self.images.all()

    def get_videos(self):
        return self.videos.all()


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField('Изображение', upload_to='products/')
    is_main = models.BooleanField('Основное изображение', default=False)
    order = models.PositiveIntegerField('Порядок', default=0)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        ordering = ('order', 'created')

    def __str__(self):
        return f'Изображение для {self.product.name}'


class ProductVideo(models.Model):
    """Модель для видео товара с автоматической конвертацией"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='videos')
    video = models.FileField('Видео', upload_to='product_videos/',
                             help_text='Загрузите видео (поддерживаются MP4, MOV, AVI, WebM, OGG)')
    title = models.CharField('Название видео', max_length=200, blank=True, null=True)
    is_main = models.BooleanField('Основное видео', default=False)
    order = models.PositiveIntegerField('Порядок', default=0)
    created = models.DateTimeField(auto_now_add=True)
    converted = models.BooleanField('Сконвертировано', default=False)
    thumbnail = models.ImageField('Превью', upload_to='product_videos/thumbnails/', blank=True, null=True)

    class Meta:
        verbose_name = 'Видео товара'
        verbose_name_plural = 'Видео товаров'
        ordering = ('order', 'created')

    def __str__(self):
        return f'Видео для {self.product.name}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.converted and self.video:
            self.convert_to_mp4()

    def get_ffmpeg_path(self):
        """Возвращает путь к ffmpeg"""
        # Пробуем найти ffmpeg
        possible_paths = [
            'ffmpeg',
            'C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe',
            'C:\\Users\\user\\AppData\\Local\\Microsoft\\WinGet\\Packages\\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\\ffmpeg-9.0-full_build\\bin\\ffmpeg.exe',
        ]
        for path in possible_paths:
            try:
                subprocess.run([path, '-version'], capture_output=True, check=True)
                return path
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue
        return 'ffmpeg'  # Если не нашли, пробуем просто ffmpeg

    def convert_to_mp4(self):
        """Конвертирует видео в MP4 формат с помощью ffmpeg"""
        try:
            video_path = self.video.path
            ext = os.path.splitext(video_path)[1].lower()

            if ext in ['.mp4', '.m4v']:
                self.converted = True
                self.save()
                return

            output_path = os.path.splitext(video_path)[0] + '.mp4'
            thumbnail_path = os.path.splitext(video_path)[0] + '.jpg'

            ffmpeg_cmd = self.get_ffmpeg_path()

            # Конвертация видео
            cmd = [
                ffmpeg_cmd,
                '-i', video_path,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'medium',
                '-crf', '23',
                '-movflags', '+faststart',
                '-y',
                output_path
            ]

            print(f'Конвертация видео: {video_path} -> {output_path}')
            print(f'Команда: {" ".join(cmd)}')

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f'Ошибка ffmpeg: {result.stderr}')
                raise Exception(f'ffmpeg error: {result.stderr}')

            # Создание превью (первый кадр)
            cmd_thumb = [
                ffmpeg_cmd,
                '-i', video_path,
                '-ss', '1',
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                thumbnail_path
            ]

            try:
                subprocess.run(cmd_thumb, capture_output=True, check=True)
                with open(thumbnail_path, 'rb') as f:
                    self.thumbnail.save(
                        os.path.basename(thumbnail_path),
                        File(f),
                        save=False
                    )
                os.remove(thumbnail_path)
            except Exception as e:
                print(f'Ошибка создания превью: {e}')

            # Замена файла
            with open(output_path, 'rb') as f:
                self.video.save(
                    os.path.basename(output_path),
                    File(f),
                    save=False
                )

            if os.path.exists(output_path):
                os.remove(output_path)

            self.converted = True
            self.save()
            print(f'Видео успешно сконвертировано: {output_path}')

        except Exception as e:
            print(f'Ошибка конвертации: {e}')
            self.converted = True
            self.save()

    def get_video_extension(self):
        if self.video:
            return self.video.name.split('.')[-1].lower()
        return None

    def get_video_type(self):
        ext = self.get_video_extension()
        if ext in ['mp4', 'm4v']:
            return 'video/mp4'
        elif ext in ['webm']:
            return 'video/webm'
        elif ext in ['ogv', 'ogg']:
            return 'video/ogg'
        return 'video/mp4'


class ProductSize(models.Model):
    """Модель для размеров товара"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sizes')
    size = models.CharField('Размер', max_length=20)
    quantity = models.PositiveIntegerField('Количество', default=0)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = 'Размер товара'
        verbose_name_plural = 'Размеры товаров'
        ordering = ('size',)

    def __str__(self):
        return f'{self.product.name} - {self.size}'


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorited_by')
    added = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные товары'
        ordering = ('-added',)

    def __str__(self):
        return f'{self.user.email} - {self.product.name}'


class Review(models.Model):
    """Модель для отзывов на товары"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviews')
    rating = models.PositiveSmallIntegerField('Оценка', choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField('Комментарий')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField('Одобрено', default=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ('-created',)
        unique_together = ('product', 'user', 'order')

    def __str__(self):
        return f'{self.user.email} - {self.product.name} - {self.rating}⭐'