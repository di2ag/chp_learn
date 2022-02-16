import tqdm
import time
import numpy as np
import pickle
import signal
import compress_pickle
import ray
from ray.util.placement_group import placement_group
import logging

from pybkb.common.bayesianKnowledgeBase import bayesianKnowledgeBase as BKB
from pybkb.python_base.reasoning.reasoning import updating
from pybkb.python_base.generics.mp_utils import MPLogger

BKB_PATHS = [
        '/home/public/data/ncats/disgenet/tcga_reactome_pathway_bkfs_ed/collapse.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/tcga-all/Wed-08-Dec-2021_h21-m13-s14/collapsed_2-16-2022.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/UMLS:C0001416/Tue-15-Feb-2022_h17-m48-s04/collapsed.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/UMLS:C0001442/Tue-15-Feb-2022_h18-m39-s39/collapsed.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/UMLS:C0003907/Tue-15-Feb-2022_h19-m27-s46/collapsed.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/UMLS:C0004576/Tue-15-Feb-2022_h20-m16-s05/collapsed.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/UMLS:C0005683/Tue-15-Feb-2022_h21-m04-s22/collapsed.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/UMLS:C0006666/Tue-15-Feb-2022_h21-m53-s43/collapsed.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/UMLS:C0006705/Tue-15-Feb-2022_h22-m41-s49/collapsed.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/UMLS:C0007852/Tue-15-Feb-2022_h23-m28-s50/collapsed.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/UMLS:C0008043/Wed-16-Feb-2022_h00-m16-s09/collapsed.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/UMLS:C0009730/Wed-16-Feb-2022_h01-m03-s36/collapsed.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/UMLS:C0011304/Wed-16-Feb-2022_h01-m50-s44/collapsed.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/UMLS:C0012359/Wed-16-Feb-2022_h02-m38-s06/collapsed.bkb',
        #'/home/public/data/ncats/structure_learning/ed_bkbs/UMLS:C0015398/Wed-16-Feb-2022_h03-m25-s39/collapsed.bkb',
        ]

TIMEOUT = 60
NUMBER_OF_WORKERS_PER_NODE = 5
NUMBER_OF_NODES = 12


def handler(signum, frame):
    raise TimeoutError('Reached timeout.')

@ray.remote(num_cpus=1)
def run_batch_update(targets, timeout, bkb_path, worker_id):
    # Register signal function handler
    signal.signal(signal.SIGALRM, handler)

    # Setup logger
    logger = MPLogger('Updater', logging.INFO, id=worker_id, loop_report_time=60)
    
    # Load BKB
    logger.info('Loading BKB.')
    col_bkb = BKB().load(bkb_path, use_pickle=True)
    logger.info('BKB Loaded')

    # Get results
    results = {'contributions': {}, 'updates': {}}
    times = {}
    timeouts = []
    logger.initialize_loop_reporting()
    for idx, target in enumerate(targets):
        logger.report(i=idx, total=len(targets))
        signal.alarm(timeout)
        start_time = time.time()
        try:
            res = updating(col_bkb, {}, [target])
        except TimeoutError:
            timeouts.append(target)
            continue
        except RecursionError:
            times[target] = -1
            continue
        results['updates'][target] = res.process_updates()
        results['contributions'][target] = res.process_inode_contributions(include_srcs=False)
        times[target] = time.time() - start_time
    return {'r': results, 't': times, 'to': timeouts}

# Setup Cluster
ray.init(address='auto')
# Create bundles
bundles = [{"CPU": NUMBER_OF_WORKERS_PER_NODE} for _ in range(NUMBER_OF_NODES)]

# Create Placement Group
pg = placement_group(bundles, strategy='STRICT_SPREAD')

# Wait for the placement group to be ready
ray.get(pg.ready())

for BKB_PATH in BKB_PATHS:
    # Get disease name from path
    #disease = BKB_PATH.split('/')[7]
    disease = 'reactome'
    print(f'Working on disease: {disease}')
    # Setup Work
    col_bkb = BKB().load(BKB_PATH, use_pickle=True)
    targets = np.array([target for target in col_bkb.getAllComponentNames() if 'Source' not in target])
    batch_targets = np.array_split(targets, NUMBER_OF_NODES*NUMBER_OF_WORKERS_PER_NODE)
    refs = [run_batch_update.remote(batch, TIMEOUT, BKB_PATH, i) for i, batch in enumerate(batch_targets)]

    unfinished = refs
    results = {'contributions': {}, 'updates': {}}
    times = {}
    timeouts = []
    while unfinished:
        finished, unfinished = ray.wait(unfinished)
        res = ray.get(finished)[0]
        _results = res['r']
        _times = res['t']
        _timeouts = res['to']
        # Merge
        results['contributions'].update(_results['contributions'])
        results['updates'].update(_results['updates'])
        times.update(_times)
        timeouts.extend(_timeouts)

    print('Saving out results.')
    with open(f'/tmp/gene_no_disease_contributionsi_{disease}.pk', 'wb') as f_:
        compress_pickle.dump((results, times, timeouts), f_, compression='lz4')
    print(f'Number of Timeouts for {disease}: {len(timeouts)}')

'''
# Register signal function handler
signal.signal(signal.SIGALRM, handler)

results = {'contributions': {}, 'updates': {}}
times = {}
timeouts = []
for target in tqdm.tqdm(sorted(col_bkb.getAllComponentNames(), reverse=True)):
    if 'Source' in target:
        continue
    signal.alarm(TIMEOUT)
    start_time = time.time()
    try:
        res = updating(col_bkb, {}, [target])
    except TimeoutError:
        timeouts.append(target)
        continue
    except RecursionError:
        times[target] = -1
        continue
    results['updates'][target] = res.process_updates()
    results['contributions'][target] = res.process_inode_contributions(include_srcs=False)
    times[target] = time.time() - start_time

print('Finished first passed.')
signal.alarm(0)
print(timeouts)
"""
print('Now unsetting timeouts and running leftover updates.')

for target in tqdm.tqdm(timeouts):
    start_time = time.time()
    try:
        res = updating(col_bkb, {}, [target])
    except RecursionError:
        times[target] = -1
        continue
    results[target] = res
    times[target] = time.time() - start_time

finished_times = [t for target, t in times.items() if t != np.inf and t >= 0]

print(f'Average Reasoning time: {np.average(finished_times)}')
print(f'Number of updates finished within {TIMEOUT} seconds: {len(finished_times)}')

with open('/tmp/test_gene_ed_times.pk', 'wb') as f_:
    pickle.dump(times, f_)
"""
print('Saving out results.')
with open('/tmp/gene_no_disease_contributions.pk', 'wb') as f_:
    compress_pickle.dump(results, f_, compression='lz4')

print('Complete')
'''
