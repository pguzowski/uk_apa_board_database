#!/usr/bin/env python

"""
usage: upload_position_measurements.py [list of files]
read position measurement lines from csv files,
and upload to the database
will fail if those boards do not exist in the database, or already have position measurements
"""


import json
import requests
import os
import csv
import sys
import datetime

from sietch_config import board_component_name
from camelcase import camelcase

def upload(list_of_measurement_files):

    measurements = {}
    header_batch = 'BATCH_ID'
    header_board = 'BOARD_ID'
    header_time = 'Measurement time'
    for f in list_of_measurement_files:
        headers = []
        with open(f) as fl:
            cf = csv.reader(fl)
            for row in cf:
                if len(headers) == 0:
                    headers = row
                    for pos,h in enumerate(headers):
                        if h == header_batch: pos_batch = pos
                        if h == header_board: pos_board = pos
                        if h == header_time: pos_time = pos
                elif len(row) > 0: # there could be empty rows
                    if len(row[pos_batch]) == 0:
                        # Tolerance rows in csv file
                        continue
                    batch = int(row[pos_batch])
                    board = int(row[pos_board])
                    time = str(datetime.datetime.strptime(row[pos_time], '%m/%d/%Y %I:%M:%S %p'))
                    if batch not in measurements.keys():
                        measurements[batch] = {}
                    if board not in measurements[batch].keys():
                        measurements[batch][board] = {'measurements':{ 'measurementTime':time }}
                    for i in range(len(row)):
                        h = headers[i]
                        if ':' in h and h.split(':')[0] in ['1','2']:
                            hd = h.split(':')[1]
                            hd_camelcase = camelcase(hd)
                            measurements[batch][board]['measurements']['position'+hd_camelcase] = float(row[i])

    with open('config.dat') as conf_file:
        config = json.load(conf_file)
        baseurl = config['url']

    header = { 'content-type': 'application/json' }

    r = requests.post(baseurl+'/machineAuthenticate',json=config['auth'],headers=header)
    if not r:
        raise Exception(r.text)

    token=r.text

    header['authorization']='Bearer '+token

    has_bad_boards = False
    for batch in measurements:
        for board in measurements[batch]:
            search_payload = {
                    'data.batchId':batch,
                    'data.boardId':board,
                    }
            r = requests.post(baseurl+'/api/search/component/'+board_component_name,json=search_payload,headers=header)

            if not r:
                raise Exception(r.text)

            results = r.json()

            if len(results) == 0:
                #bad_boards.append(batch,board,len(results))
                has_bad_boards = True
                print(f"No board found with batch ID {batch} board ID {board}", file=sys.stderr)
            elif len(results) > 1:
                #bad_boards.append(batch,board,len(results))
                has_bad_boards=True
                print(f"Multiple boards exist with batch ID {batch} board ID {board}!", file=sys.stderr)
            else:
                r = results.pop()
                uuid = r['componentUuid']
                measurements[batch][board]['uuid']=uuid


    if has_bad_boards:
        raise Exception("Bad board configurations found!")

    for batch in measurements:
        for board in measurements[batch]:
            uuid = measurements[batch][board]['uuid']
            r = requests.get(baseurl+'/api/component/'+uuid,headers=header)
            if not r:
                raise Exception(r.text)

            payload = r.json()

            for k in list(payload):
                if k != 'type' and k != 'data':
                    payload.pop(k)
            
            key='qcPositionMeasurements'
            timekey = 'measurementTime'
            if key in payload['data'] \
                    and len(payload['data'][key])>0 \
                    and timekey in payload['data'][key].keys() \
                    and len(payload['data'][key][timekey]) > 0:
                print(f"Batch {batch} board {board} already has position measurents, not overwriting!",file=sys.stderr)
                has_bad_boards = True
                continue
            
            payload['data'][key]=measurements[batch][board]['measurements']
            measurements[batch][board]['payload'] = payload

    if has_bad_boards:
        raise Exception("Boards with previous measurements found, not overwriting!")

    for batch in measurements:
        for board in measurements[batch]:
            uuid = measurements[batch][board]['uuid']
            payload = measurements[batch][board]['payload']
            
            r = requests.post(baseurl+'/api/component/'+uuid,json=payload,headers=header)
            if not r:
                raise Exception(r.text)
            print(f"Uploaded QC position measurements for batch {batch} board {board}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('files',help='CSV files to parse',nargs='+')
    args = parser.parse_args()
    upload(args.files)

if __name__ == '__main__':
    main()
