from django.db import migrations


def create_agents_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="Agents")


def delete_agents_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Agents").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_agent"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_agents_group, delete_agents_group),
    ]
