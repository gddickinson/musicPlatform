#!/bin/bash
export DYLD_LIBRARY_PATH=/opt/anaconda3/envs/flika/lib/python3.11/site-packages/pyo:/opt/anaconda3/envs/flika/lib/python3.11/site-packages/pygame/.dylibs:$DYLD_LIBRARY_PATH
python main.py
