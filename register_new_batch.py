#!/usr/bin/env python

"""
usage: register_new_batch.py -B [batch] -N [number of boards] -t [type of board]
Register a new batch of boards in the system.
"""

import json
import requests
import os
import sys

from board_types import types
from sietch_config import batch_component_name, board_component_name

def upload(batch, number, type_of_board):

    with open('config.dat') as conf_file:
        config = json.load(conf_file)
        baseurl = config['url']

    header = { 'content-type': 'application/json' }

    r = requests.post(baseurl+'/machineAuthenticate',json=config['auth'],headers=header)
    if not r:
        raise Exception(r.text)

    token=r.text

    header['authorization']='Bearer '+token

    payload={
        'data.batchId':batch,
        }

    r = requests.post(baseurl+'/api/search/component/'+batch_component_name,json=payload,headers=header)

    if not r:
        raise Exception(r.text)

    results = r.json()

    if len(results) > 0:
        raise Exception("This batch has already been registered")

    r = requests.get(baseurl+'/api/generateComponentUuid',headers=header)
    if not r:
        raise Exception(r.text)

    uuid = r.json()
    payload = {
            'type':batch_component_name,
            'data':{
                'name':f"Batch {batch}",
                'batchId':batch,
                'number':number,
                'boardType':types[type_of_board],
                },
            }
    r = requests.post(baseurl+'/api/component/'+uuid,json=payload,headers=header)
    if not r:
        raise Exception("Failed to register batch!")

    failed_registrations = []
    for board in range(1,number+1):

        payload={
            'data.batchId':batch,
            'data.boardId':board,
            }

        r = requests.post(baseurl+'/api/search/component/'+board_component_name,json=payload,headers=header)

        if not r:
            raise Exception(r.text)

        results = r.json()

        if len(results) > 0:
            print(f"Batch {batch} board {board} has already been registered!",file=sys.stderr)
            failed_registrations.append(board)
            continue

        r = requests.get(baseurl+'/api/generateComponentUuid',headers=header)
        if not r:
            raise Exception(r.text)

        uuid = r.json()
        payload = {
                'type':board_component_name,
                'data':{
                    'name':f"Batch {batch} board {board}",
                    'batchId':batch,
                    'boardId':board,
                    'boardType':types[type_of_board],
                    'boardStatus':'received'
                    },
                }
        r = requests.post(baseurl+'/api/component/'+uuid,json=payload,headers=header)
        if not r:
            print(f"Warning! Failed to register batch {batch} board {board}!!! Please run with standalone registration",file=sys.stderr)
            failed_registrations.append(board)

    nreg = number-len(failed_registrations)
    print(f"Registered batch {batch} with {nreg} boards")
    if len(failed_registrations) > 0:
        raise Exception(f"Failed to register following board IDs: {failed_registrations}. Please check logs and attempt standalone board registrations")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-B','--batch',help='Batch number',type=int,required=True)
    parser.add_argument('-N','--number',help='Total number of boards (will be labelled from 1 to N)',type=int,required=True)
    parser.add_argument('-t','--type',help='Board type ([H]ead or [E]dge; [X|V|U|G] layer; subtype [1|2|3|4|5|6])',choices=types.keys(),required=True)
    args = parser.parse_args()
    upload(args.batch,args.number,args.type)

if __name__ == '__main__':
    main()
