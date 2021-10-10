#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
version: 1.0 
Author: Ledivan B. Marques
    Email:	ledivan.marques@contaquanto.com.br
This module is for validating user's input
"""

import re

def is_valid_grafana_host(url):
    if type(url) is not str:
        raise TypeError("GRAFANA_HOST should be a string")
    regex = '^(([a-z0-9]|[a-z0-9][a-z0-9\-]*[a-z0-9])\.)*([a-z0-9]|[a-z0-9][a-z0-9\-]*[a-z0-9])(:[0-9]+)?$'
    match_obj = re.search(regex, url)
    if match_obj is not None and match_obj.group() is not None:
        return True
    raise ValueError("GRAFANA_HOST is invalid: {}".format(url))

def is_valid_grafana_api_token(url):
    if type(url) is not str:
        raise TypeError("API token should be a string")
    return True