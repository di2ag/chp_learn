# Generated by Django 4.0.3 on 2022-03-10 12:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('chp_learn', '0005_alter_disease_fill_g2dis_results_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='diseasetofillgeneresult',
            old_name='relation',
            new_name='predicate',
        ),
        migrations.RenameField(
            model_name='genetofillgeneresult',
            old_name='relation',
            new_name='predicate',
        ),
    ]
