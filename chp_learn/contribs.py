import numpy as np
import math
import tqdm
import re
import itertools
from collections import defaultdict

def extract_state_range(state):
    split = re.split('-|\[|\]|\(|\)', state)
    for s in split:
        try:
            r = float(s)
            break
        except:
            continue
    return r

def remap_bkb(bkb):
    remap = {}
    for comp_idx in bkb.getAllComponentIndices():
        comp_name = bkb.getComponentName(comp_idx)
        if 'Source' in comp_name:
            continue
        states = []
        for state_idx in bkb.getAllComponentINodeIndices(comp_idx):
            states.append(bkb.getComponentINodeName(comp_idx, state_idx))
        # Sort states 
        states = sorted([(extract_state_range(state), state) for state in states], key=lambda x: x[0])
        states_map = {states[0][1]: 'LOW', states[-1][1]: 'HIGH'}
        remap[comp_name] = states_map
    return remap

def get_regulation_weights(res, bkb, log_probs=True):
    remap = remap_bkb(bkb)
    up_weights = defaultdict(lambda: defaultdict(int))
    down_weights = defaultdict(lambda: defaultdict(int))
    for target in tqdm.tqdm(res['contributions'], desc='Calculating G2G weights'):
        contrib_dict = res['contributions'][target]
        updates = res['updates'][target]
        for (comp, state), state_contrib_dict in contrib_dict.items():
            if remap[comp].get(state, None) and remap[comp].get(state, None) == 'LOW':
                for (other_comp, other_state), contrib in state_contrib_dict.items():
                    if other_comp == comp:
                        continue
                    if remap[other_comp].get(other_state, None) and remap[other_comp].get(other_state) == 'LOW':
                        up_weights[comp][other_comp] += math.log(contrib) - math.log(updates[comp][state])
                    elif remap[other_comp].get(other_state, None) and remap[other_comp].get(other_state) == 'HIGH':
                        down_weights[comp][other_comp] += math.log(contrib) - math.log(updates[comp][state])
                    else:
                        continue
            elif remap[comp].get(state, None) and remap[comp].get(state, None) == 'HIGH':
                for (other_comp, other_state), contrib in state_contrib_dict.items():
                    if other_comp == comp:
                        continue
                    if remap[other_comp].get(other_state, None) and remap[other_comp].get(other_state) == 'LOW':
                        down_weights[comp][other_comp] += math.log(contrib) - math.log(updates[comp][state])
                    elif remap[other_comp].get(other_state, None) and remap[other_comp].get(other_state) == 'HIGH':
                        up_weights[comp][other_comp] += math.log(contrib) - math.log(updates[comp][state])
                    else:
                        continue
            else:
                continue
    return up_weights, down_weights
    

def get_contribution_weight_expression(inode_contrib_dict, updates, bkb, log_contribs=True):
    contrib_state_map = {}
    # First build a map
    for target, contrib_dict in inode_contrib_dict.items():
        for contrib_inode, contrib in contrib_dict.items():
            contrib_comp, contrib_state = contrib_inode
            if contrib_comp in contrib_state_map:
                continue
            comp_idx = bkb.getComponentIndex(contrib_comp)
            assert comp_idx != -1
            contrib_state_map[contrib_comp] = [bkb.getComponentINodeName(comp_idx, i) for i in range(bkb.getNumberComponentINodes(comp_idx))]
    # Now fill the map with appropriate weight vectors
    weight_dict = defaultdict(dict)
    for target, contrib_dict in inode_contrib_dict.items():
        for contrib_inode, contrib in contrib_dict.items():
            relative_contrib = contrib / updates[target]
            if log_contribs:
                contrib = math.log(relative_contrib)
            contrib_comp, contrib_state = contrib_inode
            if contrib_comp == target:
                continue
            weight_array = np.zeros(len(contrib_state_map[contrib_comp]))
            weight_array[contrib_state_map[contrib_comp].index(contrib_state)] = relative_contrib
            weight_dict[target][contrib_comp] = weight_array
    # Now calculate weight
    weights = defaultdict(int)
    for target1, target2 in itertools.combinations(weight_dict, r=2):
        for contrib_comp in set.union(set(weight_dict[target1].keys()), set(weight_dict[target2].keys())):
            if contrib_comp not in weight_dict[target1]:
                weight_arr1 = None
            else:
                weight_arr1 = weight_dict[target1][contrib_comp]
            if contrib_comp not in weight_dict[target2]:
                weight_arr2 = None
            else:
                weight_arr2 = weight_dict[target2][contrib_comp]
            assert not (weight_arr1 is None and weight_arr2 is None)
            # Do another preprocess check for any none arrays
            if weight_arr1 is None:
                weight_arr1 = np.zeros_like(weight_arr2)
            if weight_arr2 is None:
                weight_arr2 = np.zeros_like(weight_arr1)
            # Now do a euclidean distance
            weights[contrib_comp] += np.linalg.norm(weight_arr1 - weight_arr2)
    return weights
            


            


            

