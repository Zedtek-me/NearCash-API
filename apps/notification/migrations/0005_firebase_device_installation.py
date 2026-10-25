from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("notification", "0004_firebasedevice")]

    operations = [
        migrations.AddField(
            model_name="firebasedevice",
            name="installation_id",
            field=models.CharField(blank=True, max_length=255, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="firebasedevice",
            name="platform",
            field=models.CharField(
                blank=True,
                choices=[("web", "Web"), ("android", "Android"), ("ios", "iOS")],
                max_length=20,
                null=True,
            ),
        ),
    ]
