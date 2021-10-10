#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
version: 1.0 
Author: Ledivan B. Marques
    Email:	ledivan_bernardo@yahoo.com.br
"""
import logging
logging.basicConfig(format='%(asctime)s - %(levelname)s : %(message)s', level=logging.INFO)
logging.getLogger().setLevel(logging.INFO)
import json
import os
import requests
import input_validator

print('Configure your environment variables')
print('Your grafana host without protocol specification (e.g. localhost:3000). ')
GRAFANA_HOST = input('Enter your GRAFANA_HOST:')
print('Your grafana editor/admin API key, find or create one under Configuration -> API keys.')
GRAFANA_TOKEN = input('Enter your GRAFANA_TOKEN:')
print('Your grafana editor/admin API key, find or create one under Configuration -> API keys.')
GRAFANA_HOST_DST = input('Enter your GRAFANA_HOST_DST:')
print('Your grafana editor/admin API key, find or create one under Configuration -> API keys.')
GRAFANA_TOKEN_DST = input('Enter your GRAFANA_TOKEN_DST:')
print('Your grafana editor/admin API key, find or create one under Configuration -> API keys.')

dirName = "dashboards"

REQUEST_HEADERS = {
    'Authorization': 'Bearer {}'.format(GRAFANA_TOKEN),
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache',
    'User-Agent': None
}

REQUEST_HEADERS_DST = {
    'Authorization': 'Bearer {}'.format(GRAFANA_TOKEN_DST),
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache',
    'User-Agent': None
}

ALERTS = []
SUPPORTED_PANELS = ['graph', 'grafana-worldmap-panel', 'grafana-piechart-panel', 'singlestat', 'dashlist',
                    'alertlist', 'text', 'heatmap', 'bargauge', 'table', 'gauge', 'stat', 'row']

# validate inputs
input_validator.is_valid_grafana_host(GRAFANA_HOST)
input_validator.is_valid_grafana_api_token(GRAFANA_TOKEN)

input_validator.is_valid_grafana_host(GRAFANA_HOST_DST)
input_validator.is_valid_grafana_api_token(GRAFANA_TOKEN_DST)

BASE_URL = f'https://{GRAFANA_HOST}/api'
UPLOAD_DASHBOARD_URL = f'https://{GRAFANA_HOST_DST}/api/dashboards/db'
ALL_DASHBOARDS_URL = f'https://{GRAFANA_HOST}/api/search'

# set dashboard values before upload and creating new dashboard with grafana api
def _init_parameters(dashboard, fid):
    try:
        dashboard['overwrite'] = True
        dashboard['folderId'] = fid
        dashboard['dashboard']['id'] = None
        dashboard['dashboard']['editable'] = True
        dashboard['dashboard']['uid'] = None
        dashboard['dashboard']['refresh'] = "30s"
    except KeyError as e:
        logging.error(
            'At `{}` dashboard, error occurred while setting dashboard parameters'.format(dashboard['dashboard'],
                                                                                          ['title']))

def _check_exists():
    list_exists = []
    exists_dash = requests.get(f'https://{GRAFANA_HOST_DST}/api' + '/search',headers=REQUEST_HEADERS_DST)
    for title_exists in exists_dash.json():
        list_exists.append(title_exists["title"])
    return list_exists

# Get all dashboards as json from grafana host
def _init_dashboard_list(uid_list, base_url, r_headers):
    dashboards_list = []
    for uid in uid_list:
        request_url = f'{base_url}/dashboards/uid/{uid}'
        response = requests.get(request_url, headers=r_headers)
        dashboard = response.json()
        file_name = dashboard["dashboard"]['title']
        dash_title = file_name.replace('/','') + '.json'
        if not os.path.exists(dirName):
           os.mkdir(dirName)
        with open(dirName+"/"+dash_title, 'w') as json_file:
            json_file.write(json.dumps(dashboard["dashboard"], sort_keys=True, indent=4, separators=(',', ': ')))
        try:
            del dashboard['meta']
        except KeyError:
            pass
        if file_name not in _check_exists():
            dashboards_list.append(dashboard)
    return dashboards_list

# Creates new folder for uploaded dashboards, if the folder already exists, the dashboards in the folder wil be overwriten
def _create_uploaded_folder():
    folder_url = 'https://{}/api/folders'.format(GRAFANA_HOST_DST)
    folder_id = None
    new_title = "General"
    folders_list = json.loads(requests.get(folder_url, params={}, headers=REQUEST_HEADERS_DST).text)
    print(folders_list)
    for folder in folders_list:
        if folder['title'] == new_title:
            folder_id = folder['id']
            logging.info('Found existing `Uploaded by script` folder with id: {}'.format(str(folder_id)))
    if not folder_id:
        folder_data = {
            "uid": None,
            "title": new_title
        }
        if new_title not in "General":
            new_folder = requests.post(url=folder_url, json=folder_data, params={}, headers=REQUEST_HEADERS_DST).json()
            folder_id = new_folder['id']
            logging.info('New folder created with id: {}'.format(str(folder_id)))

    return folder_id


# Adding panel types to dedicated list
def _get_panel_types(panels, panel_types):
    for panel in panels:
        try:
            panel_types.append(panel['type'])
        except Exception as e:
            logging.error(e)


# check for unsupported panel types
def _inspect_panels_types(dashboard):
    panel_types = []
    _get_panel_types(dashboard['dashboard']['panels'], panel_types)
    panel_types = list(dict.fromkeys(panel_types))
    for t in panel_types:
        if t not in SUPPORTED_PANELS:
            alert = f"`{t}` panel type is not supported, at `{dashboard['dashboard']['title']}` dashboard: you may " \
                    f"experience some issues when rendering the dashboard "
            ALERTS.append(alert)


def _clear_notifications(dashboard):
    for panel in dashboard['dashboard']['panels']:
        try:
            panel['alert']['notifications'] = []
        except KeyError:
            pass

# Checking panels for Static datasource reference, will create dynamic datasource variable if not exists
def _validate_templating(dashboard):
    try:
        var_list = dashboard['dashboard']['templating']['list']
        has_ds = False
        for var in var_list:
            if var['type'] == 'datasource' and var['query'] == 'prometheus':
                has_ds = True
                datasource_name = var['name']
        if not has_ds:
            new_ds = {
                'name': 'datasource',
                'type': 'datasource',
                'query': 'prometheus'
            }
            datasource_name = new_ds['name']
            var_list.append(new_ds)
        dashboard['dashboard']['templating']['list'] = var_list
    except KeyError as e:
        logging.info('At `{}` dashboard - an error has occurred while editing the dashboard: {}'.format(
            dashboard['dashboard']['title'], e))
    
# main script
def main():
    all_dashboards = requests.get(ALL_DASHBOARDS_URL, headers=REQUEST_HEADERS).json()
    uids = []
    for item in all_dashboards:
        try:
            if item['type'] == 'dash-db':
                uids.append(item['uid'])
        except TypeError as e:
            raise TypeError(all_dashboards['message'])
    # init list
    dashboards_list = _init_dashboard_list(uids, BASE_URL, REQUEST_HEADERS)
    # create new folder to store the dashboards
    folder_id = _create_uploaded_folder()
    for dashboard in dashboards_list:
        if "rows" not in dashboard['dashboard'].keys() or dashboard['dashboard']['schemaVersion'] > 14:
            _init_parameters(dashboard, folder_id)
            _validate_templating(dashboard)
            _inspect_panels_types(dashboard)
            _clear_notifications(dashboard)
            try:
                upload_response = requests.post(url=UPLOAD_DASHBOARD_URL, data=json.dumps(dashboard), params={},
                                                headers=REQUEST_HEADERS_DST)
            except Exception as e:
                logging.error("At `{}` dashboard - upload error : {}".format(dashboard['dashboard']['title'], e))
            if upload_response.ok:
                logging.info("`{}` dashboard uploaded successfully, schema version: {}, status code: {}".format(
                    dashboard['dashboard']['title'], dashboard['dashboard']['schemaVersion'],
                    upload_response.status_code))
            else:
                logging.error(
                    'At `{}` dashboard - upload error: {} - schema version: {}'.format(dashboard['dashboard']['title'],
                                                                                       upload_response.text,
                                                                                       dashboard['dashboard'][
                                                                                           'schemaVersion']))
        else:
            ALERTS.append(
                'cannot parse "rows" object, At `{}` dashboard: please consider to update the dashboard schema '
                'version ️, current version: {}'.format(dashboard['dashboard']['title'], dashboard[
                    'dashboard']['schemaVersion']))
    for alert in sorted(ALERTS):
       logging.warning(alert)

if __name__ == "__main__":
    main()