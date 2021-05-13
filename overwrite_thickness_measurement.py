#!/usr/bin/env python

"""
usage: overwrite_thickness_measurement.py -B [batch] -b [board] [file]
read a thickness measurement csv file,
and overwrite the database with that batch and board id and position label
will fail if that board doesn't already have this position measurement in the database
(use upload in that case)
"""


import json
import requests
import os

from sietch_config import board_component_name

def upload(batch, board, measurement_file):

    measurements = {}
    for f in [measurement_file]:
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

    existing_measurements = [existing_measurement['measurementLabel'] for existing_measurement in payload['data'][key]]
    for m in measurements:
        if m not in existing_measurements:
            print(f"WARNING! measurement {name} is not in the database! please use upload script!")
            measurements.pop(name)

    if len(measurements) == 0:
        print("No data to upload")
        return

    for m in measurements:
        for em in payload['data'][key]:
            if em['measurementLabel'] == m:
                em['measurement'] = measurements[m]

    r = requests.post(baseurl+'/api/component/'+uuid,json=payload,headers=header)
    if not r:
        raise Exception(r.text)
    print(f"Overwritten batch {batch} board {board} measurement {fn}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-B','--batch',help='Batch number',type=int,required=True)
    parser.add_argument('-b','--board',help='Board number',type=int,required=True)
    parser.add_argument('file',help='CSV file to parse')
    args = parser.parse_args()
    upload(args.batch,args.board,args.file)

if __name__ == '__main__':
    main()
