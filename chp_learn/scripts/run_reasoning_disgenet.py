import tqdm
import time
import numpy as np
import pickle
import signal
import compress_pickle
import ray
import os
from ray.util.placement_group import placement_group
import logging
from datetime import datetime

from pybkb.common.bayesianKnowledgeBase import bayesianKnowledgeBase as BKB
from pybkb.python_base.reasoning.reasoning import updating
from pybkb.python_base.generics.mp_utils import MPLogger


# Set BKB Base Path
BKB_BASE_PATH = '/home/public/data/ncats/structure_learning/ed_bkbs'
# Set Result Saving Path
SAVE_PATH = '/home/public/data/ncats/chp_db/chp_learn'

BKB_PATHS = []
# Add any additional paths you want to process
#BKB_PATHS += '/home/public/data/ncats/disgenet/tcga_reactome_pathway_bkfs_ed/collapse.bkb',

# Get Disease BKB paths
most_recent = None
for root, dirnames, files in os.walk(BKB_BASE_PATH):
    if 'UMLS' in root and len(files) == 0:
        most_recent = sorted([(datetime.strptime(dirname, '%a-%d-%b-%Y_h%H-m%M-s%S'), dirname) for dirname in dirnames])[-1][-1]
        continue
    if most_recent and most_recent in root:
        BKB_PATHS.append(os.path.join(root, files[0]))

TIMEOUT = 60
NUMBER_OF_WORKERS_PER_NODE = 5
NUMBER_OF_NODES = 12


def handler(signum, frame):
    raise TimeoutError('Reached timeout.')

@ray.remote(num_cpus=1)
def run_batch_update(targets, timeout, bkb_path, worker_id):
    # Register signal function handler
    #signal.signal(signal.SIGALRM, handler)

    # Setup logger
    logger = MPLogger('Updater', logging.INFO, id=worker_id, loop_report_time=60)
    
    # Load BKB
    logger.info('Loading BKB.')
    col_bkb = BKB().load(bkb_path, use_pickle=True)
    logger.info('BKB Loaded')

    # Get results
    results = {'contributions': {}, 'updates': {}}
    times = {}
    #timeouts = []
    logger.initialize_loop_reporting()
    for idx, target in enumerate(targets):
        logger.report(i=idx, total=len(targets))
        #signal.alarm(timeout)
        start_time = time.time()
        try:
            res = updating(col_bkb, {}, [target], timeout=timeout)
        #except TimeoutError:
        #    timeouts.append(target)
        #    continue
        except RecursionError:
            times[target] = -1
            continue
        results['updates'][target] = res.process_updates()
        results['contributions'][target] = res.process_inode_contributions(include_srcs=False)
        times[target] = time.time() - start_time
    return {
            'r': results,
            't': times,
            #'to': timeouts
            }

# Setup Cluster
ray.init(address='auto')
# Create bundles
bundles = [{"CPU": NUMBER_OF_WORKERS_PER_NODE} for _ in range(NUMBER_OF_NODES)]

# Create Placement Group
pg = placement_group(bundles, strategy='STRICT_SPREAD')

# Wait for the placement group to be ready
ray.get(pg.ready())

# Get targets for all BKBs so we can sort and preprocess simulateously
TARGET_BKB_PATHS = []
for path in tqdm.tqdm(BKB_PATHS, desc='Preprocessing BKBs'):
    targets = [target for target in BKB().load(path, use_pickle=True).getAllComponentNames() if 'Source' not in target]
    TARGET_BKB_PATHS.append((targets, path))
TARGET_BKB_PATHS = sorted(TARGET_BKB_PATHS, key=lambda x: len(x[0]))

#for t, _ in TARGET_BKB_PATHS:
#    print(len(t))
#input()

for i, (targets, BKB_PATH) in enumerate(TARGET_BKB_PATHS):
    # Get disease name from path
    disease = BKB_PATH.split('/')[7]
    #disease = 'reactome'
    print(f'Working on disease {i+1}/{len(TARGET_BKB_PATHS)}: {disease}')
    # Setup Work
    #col_bkb = BKB().load(BKB_PATH, use_pickle=True)
    #targets = np.array([target for target in col_bkb.getAllComponentNames() if 'Source' not in target])
    targets = np.array(targets)
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
        #_timeouts = res['to']
        # Merge
        results['contributions'].update(_results['contributions'])
        results['updates'].update(_results['updates'])
        times.update(_times)
        #timeouts.extend(_timeouts)

    print('Saving out results.')
    with open(os.path.join(SAVE_PATH, f'fillgene_{disease}.pk'), 'wb') as f_:
        compress_pickle.dump((results, times, timeouts), f_, compression='lz4')
    #print(f'Number of Timeouts for {disease}: {len(timeouts)}')

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
