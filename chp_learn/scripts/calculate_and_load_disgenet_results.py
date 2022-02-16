import os
import tqdm
import time
import numpy as np
import pandas as pd
import pickle
import signal
import compress_pickle

#from chp_data.ingestion.sql_db_handler import SQL_DB_Handler
from pybkb.common.bayesianKnowledgeBase import bayesianKnowledgeBase as BKB
from pybkb.python_base.reasoning.reasoning import updating

from chp_learn.contribs import get_regulation_weights
from chp_learn.disease_gene_relations import get_disease_gene_weights
from chp_learn.models import Gene, Disease, GeneFillToGeneResult, GeneFillToDiseaseResult

base_dir = os.path.dirname(os.path.abspath(__file__))

DISGENET_DF_PATH = '/tmp/disgenet_table.pk'

def run():
    # Clear all results
    Gene.objects.all().delete()
    Disease.objects.all().delete()
    GeneFillToGeneResult.objects.all().delete()
    GeneFillToDiseaseResult.objects.all().delete()
    
    ## Load g2g results
    # Load bkb
    col_bkb = BKB().load('/home/public/data/ncats/disgenet/tcga_reactome_pathway_bkfs_ed/collapse.bkb', use_pickle=True)
    # Load I-node contributions
    g2g_result_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'g2g_reactome.pk')
    with open(g2g_result_path, 'rb') as f_:
        res, times, timeouts = compress_pickle.load(f_, compression='lz4')

    # Calcuate weights from contributions
    #weights = {target: get_regulation_weights(target, res['contributions'][target], res['updates'][target], col_bkb) for target in res['contributions']}
    up_weights, down_weights = get_regulation_weights(res, col_bkb)
    # Add g2g relations to database
    for query_gene, weights_dict in tqdm.tqdm(up_weights.items(), desc='Loading G2G UP relationships into DB'):
        qg, qg_created = Gene.objects.get_or_create(curie=query_gene)
        qg.save()
        # Fill upreguation
        for fill_gene, weight in weights_dict.items():
            fg, fg_created = Gene.objects.get_or_create(curie=fill_gene)
            fg.save()
            g2g_res = GeneFillToGeneResult(query_gene=qg, fill_gene=fg, weight=weight, relation='UP_REG')
            g2g_res.save()
    # Add g2g relations to database
    for query_gene, weights_dict in tqdm.tqdm(down_weights.items(), desc='Loading G2G DOWN relationships into DB'):
        qg, qg_created = Gene.objects.get_or_create(curie=query_gene)
        qg.save()
        # Fill downreguation
        for fill_gene, weight in weights_dict.items():
            fg, fg_created = Gene.objects.get_or_create(curie=fill_gene)
            fg.save()
            g2g_res = GeneFillToGeneResult(query_gene=qg, fill_gene=fg, weight=weight, relation='DOWN_REG')
            g2g_res.save()


    ## Load disease gene relations
    diseases = [
            'UMLS:C0004576',
            'UMLS:C0007852', 
            'UMLS:C0012359',
            'UMLS:C0001416', 
            'UMLS:C0005683',
            'UMLS:C0008043',
            'UMLS:C0015398',
            'UMLS:C0001442',
            'UMLS:C0006666',
            'UMLS:C0009730',
            'UMLS:C0003907',
            'UMLS:C0006705',
            'UMLS:C0011304',
            ]

    # Load disgenet data
    disgenet_df = pd.read_pickle(DISGENET_DF_PATH)

    for disease in diseases:
        g2d_result_path = os.path.join(base_dir, f'fillgene_{disease}.pk')
        dgs = disgenet_df[disgenet_df['diseaseId'] == disease]

        with open(g2d_result_path, 'rb') as f_:
            res, times, timeouts = compress_pickle.load(f_, compression='lz4')

        # Calcuate weights from contributions
        weights = {target: get_disease_gene_weights(target, updates, dgs) for target, updates in res['updates'].items()}

        # Add g2g relations to database
        d, d_created = Disease.objects.get_or_create(curie=disease)
        d.save()
        for fill_gene, weights_dict in tqdm.tqdm(weights.items(), desc='Loading G2D relationships into DB'):
            fg, fg_created = Gene.objects.get_or_create(curie=fill_gene)
            fg.save()
            for state, weight in weights_dict.items():
                g2d_res = GeneFillToDiseaseResult(fill_gene=fg, weight=weight, query_disease=d, relation=state)
                g2d_res.save()
