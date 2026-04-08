from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('logo', models.ImageField(blank=True, null=True, upload_to='site/')),
                ('bio_en', models.TextField(blank=True, default='A brand founded on bold femininity, offering effective and effortless products.')),
                ('bio_ar', models.TextField(blank=True, default='علامة تجارية نسائية جريئة تدعمها منتجات عالية الجودة وفعالة وسهلة الاستخدام.')),
            ],
            options={
                'verbose_name': 'Site Settings',
                'verbose_name_plural': 'Site Settings',
            },
        ),
    ]
