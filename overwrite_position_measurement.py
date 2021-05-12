#!/usr/bin/env python

import json
import requests
import os
import csv
import re
import sys
import datetime

pattern = re.compile(r'[^a-zA-Z0-9]+')
def camelcase(s):
    return pattern.sub('',s.title())

def upload(target_batch, target_board, measurement_file):

    measurements = {}
    header_batch = 'BATCH_ID'
    header_board = 'BOARD_ID'
    header_time = 'Measurement time'
    for f in [measurement_file]:
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
                    if batch != target_batch and board != target_board:
                        continue
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
            r = requests.post(baseurl+'/api/search/component/UK%20Board',json=search_payload,headers=header)

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

    has_bad_boards = True
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
                has_bad_boards = False
            
            payload['data'][key]=measurements[batch][board]['measurements']
            measurements[batch][board]['payload'] = payload

    if has_bad_boards:
        raise Exception("No previous measurements found for batch {target_batch} board {target_board}!")

    for batch in measurements:
        for board in measurements[batch]:
            uuid = measurements[batch][board]['uuid']
            payload = measurements[batch][board]['payload']
            
            r = requests.post(baseurl+'/api/component/'+uuid,json=payload,headers=header)
            if not r:
                raise Exception(r.text)
            print(f"Overwrote QC position measurements for batch {batch} board {board}")


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
