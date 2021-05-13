#!/usr/bin/env python

"""
usage: standalone_register_new_board.py -B [batch] -b [board] -t [type of board]
Register a new board of boards in the system.
This batch must already exist.
"""

import json
import requests
import os

from board_types import types
from sietch_config import batch_component_name, board_component_name

def upload(batch, board, type_of_board):

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

    if len(results) != 1:
        raise Exception("This batch has not been registered!")

    batch_uuid = results.pop()['componentUuid']

    r = requests.get(baseurl+'/api/component/'+batch_uuid,headers=header)
    if not r:
        raise Exception(r.text)

    batch_type = r.json()['data']['boardType']

    if batch_type != types[type_of_board]:
        raise Exception(f"This batch type has been registered as '{batch_type}', but you are attempting to register a board of a different type '{types[type_of_board]}'")

    payload={
        'data.batchId':batch,
        'data.boardId':board,
        }

    r = requests.post(baseurl+'/api/search/component/'+board_component_name,json=payload,headers=header)

    if not r:
        raise Exception(r.text)

    results = r.json()

    if len(results) > 0:
        raise Exception(f"Batch {batch} board {board} has already been registered!")

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
        raise Exception(f"Warning! Failed to register batch {batch} board {board}!!! Please run with standalone registration")

    print(f"Registered batch {batch} board {board}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-B','--batch',help='Batch number',type=int,required=True)
    parser.add_argument('-b','--board',help='Board number',type=int,required=True)
    parser.add_argument('-t','--type',help='Board type ([H]ead or [E]dge; [X|V|U|G] layer; subtype [1|2|3|4|5|6])',choices=types.keys(),required=True)
    args = parser.parse_args()
    upload(args.batch,args.board,args.type)

if __name__ == '__main__':
    main()
