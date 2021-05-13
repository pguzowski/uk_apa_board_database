#!/usr/bin/env python

"""
usage: upload_position_measurements.py -B [batch] -b [board] [list of files]
read thickness measurements from csv files,
and upload to the database.
Will fail if the board doesn't exist in the database.
Will not overwrite existing measurements.
"""

import json
import requests
import os

from sietch_config import board_component_name

def upload(batch, board, list_of_measurement_files):

    measurements = {}
    for f in list_of_measurement_files:
        fn = os.path.basename(f)
        fn = os.path.splitext(fn)[0]
        with open(f) as fl:
            measurements[fn] = [float(e.strip()) for e in fl.readlines()]

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
        'data.boardId':board,
        }

    r = requests.post(baseurl+'/api/search/component/'+board_component_name,json=payload,headers=header)

    if not r:
        raise Exception(r.text)

    results = r.json()

    if len(results) == 0:
        raise Exception("No board found with this batch/board number!")
    if len(results) > 1:
        raise Exception("Multiple boards exist with this batch/board number!")

    r = results.pop()
    uuid = r['componentUuid']

    r = requests.get(baseurl+'/api/component/'+uuid,headers=header)
    if not r:
        raise Exception(r.text)

    payload = r.json()

    for k in list(payload):
        if k != 'type' and k != 'data':
            payload.pop(k)
    
    key='qcThicknessMeasurements'
    if key not in payload['data']:
        payload['data'][key]=[]

    for existing_measurement in payload['data'][key]:
        name = existing_measurement['measurementLabel']
        if name in measurements.keys():
            print(f"WARNING! measurement {name} already in database! will not overwrite!")
            measurements.pop(name)

    if len(measurements) == 0:
        print("No data to upload")
        return

    for m in measurements:
        payload['data'][key].append({"measurementLabel":m,"measurement":measurements[m]})

    r = requests.post(baseurl+'/api/component/'+uuid,json=payload,headers=header)
    if not r:
        raise Exception(r.text)
    print(f"Uploaded QC thickness measurements for batch {batch} board {board}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-B','--batch',help='Batch number',type=int,required=True)
    parser.add_argument('-b','--board',help='Board number',type=int,required=True)
    parser.add_argument('files',help='CSV files to parse',nargs='+')
    args = parser.parse_args()
    upload(args.batch,args.board,args.files)

if __name__ == '__main__':
    main()
