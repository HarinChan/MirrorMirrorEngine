#!/usr/bin/env python3
"""
PenPals Application Entry Point
Simple wrapper around main.py for deployment and production use.
"""

import os
import sys
from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"