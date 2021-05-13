#!/usr/bin/env python

"""
usage: generate_label.py -B [batch] -b [board] (-d [directory])
generate label (qr code) for board, as svg file
Optionally place svg file in directory (default current directory)
"""

import json
import requests

from sietch_config import board_component_name

def upload(batch, board, dir):

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

    fullurl = baseurl + '/' + uuid

    import qrcode
    import qrcode.image.svg
    qr = qrcode.QRCode()
    qr.add_data(fullurl)
    img = qr.make_image(image_factory=qrcode.image.svg.SvgPathImage)
    img.save(f'{dir}/Batch_{batch}_board_{board}.svg')

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-B','--batch',help='Batch number',type=int,required=True)
    parser.add_argument('-b','--board',help='Board number',type=int,required=True)
    parser.add_argument('-d','--dir',help='Image output directory',default='.')
    args = parser.parse_args()
    upload(args.batch,args.board,args.dir)

if __name__ == '__main__':
    main()
