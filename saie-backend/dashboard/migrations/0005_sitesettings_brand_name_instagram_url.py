from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0004_homeimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='sitesettings',
            name='brand_name',
            field=models.CharField(blank=True, default='SLIQ', max_length=100),
        ),
        migrations.AddField(
            model_name='sitesettings',
            name='instagram_url',
            field=models.URLField(blank=True, default='https://www.instagram.com/sliq.hair/'),
        ),
    ]
