# -*- coding: utf-8 -*-
"""
@Author  : Wu
@Created on: 2026/4/28 8:39
@Remark :
"""
from waitress import serve
from application.wsgi import application

if __name__ == '__main__':
    serve(application, host='0.0.0.0', port=18000, threads=6)