import math

from trapi_model.biolink.constants import *

def get_prior_from_dsi(dsi):
    return 2**(dsi * math.log(1/30170, 2))

def extract_lower_range(state):
    for s in state.split(' '):
        try:
            t = float(s)
            break
        except:
            continue
    return t

def get_disease_gene_weights(target, updates, dgs):
    ''' Calculates weight as 
    P(Gene = {UP, NORMAL, DOWN}, Gene is related to disease | H) =
      = P(Gene = {UP, NORMAL, DOWN} | Gene is related to disease, H) * P(Gene is related to disease | H)
    '''
    # Get DSI from disgenet subtable
    try:
        _dsi = dgs[dgs['geneName'].str.contains(target)]['DSI']
        if len(_dsi) > 0:
            dsi = float(_dsi.iloc[0])
        else:
            dsi = float(_dsi)
    except Exception as ex:
        print(_dsi)
        raise ex
    # Calculate log prob weight from BKB update and DSI
    weights = {}
    for comp, state_dict in updates.items():
        for state, prob in state_dict.items():
            try:
                weights[state] = math.log(prob) + math.log(get_prior_from_dsi(dsi))
            except ValueError:
                continue
    # Parse up, normal, down regulation expression
    new_weights = {}
    states = []
    for state in weights:
        states.append((extract_lower_range(state), state))
    # Sort states
    for i, (_, state) in enumerate(sorted(states, key=lambda x: x[0])):
        if len(states) == 2:
            if i == 0:
                new_weights[BIOLINK_DECREASES_EXPRESSION_OF_ENTITY.get_curie()] = weights[state]
            else:
                new_weights[BIOLINK_INCREASES_EXPRESSION_OF_ENTITY.get_curie()] = weights[state]
        elif len(states) == 3:
            if i == 0:
                new_weights[BIOLINK_DECREASES_EXPRESSION_OF_ENTITY.get_curie()] = weights[state]
            elif i == 2:
                # There is no regulation 
                # new_weights['NO_REG'] = weights[state]
                continue
            else:
                new_weights[BIOLINK_INCREASES_EXPRESSION_OF_ENTITY.get_curie()] = weights[state]
    return new_weights
