from django.db import models

class Gene(models.Model):
    curie = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=128, null=True)
    fill_g2g_results = models.ManyToManyField('Gene', through='GeneToFillGeneResult', related_name='g2g_filled_by')
    fill_dis2g_results = models.ManyToManyField('Disease', through='DiseaseToFillGeneResult', related_name='dis2g_filled_by')

    def __str__(self):
        return str(self.curie)

class Disease(models.Model):
    curie = models.CharField(max_length=128, unique=True)
    name = models.CharField(max_length=128, null=True)
    fill_g2dis_results = models.ManyToManyField('Gene', through='GeneToFillDiseaseResult', related_name='g2dis_filled_by') 

    def __str__(self):
        return str(self.curie)

class GeneToFillGeneResult(models.Model):
    fill_gene = models.ForeignKey('Gene', on_delete=models.CASCADE, related_name='g2g_fill_gene')
    query_gene = models.ForeignKey('Gene', on_delete=models.CASCADE, related_name='g2g_query_gene')
    weight = models.FloatField()
    relation = models.CharField(max_length=128)

    def __str__(self):
        return f'{self.query_gene} -> {self.relation} -> {self.fill_gene} with weight: {self.weight}'

class GeneToFillDiseaseResult(models.Model):
    fill_disease = models.ForeignKey('Disease', on_delete=models.CASCADE, related_name='dis2g_fill_disease')
    query_gene = models.ForeignKey('Gene', on_delete=models.CASCADE, related_name='dis2g_query_gene')
    weight = models.FloatField()

class DiseaseToFillGeneResult(models.Model):
    fill_gene = models.ForeignKey('Gene', on_delete=models.CASCADE, related_name='g2dis_fill_gene')
    query_disease = models.ForeignKey('Disease', on_delete=models.CASCADE, related_name='g2dis_query_disease')
    weight = models.FloatField()
    relation = models.CharField(max_length=128)

    def __str__(self):
        return f'{self.query_disease} -> {self.relation} -> {self.fill_gene} with weight: {self.weight}'

