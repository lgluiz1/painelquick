from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0004_company_alter_complaintcategory_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
    ]
