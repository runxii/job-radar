#!/usr/bin/env bash
# set virtual env in Linux:
# sudo apt install python3.13-venv
# python3 -m venv venv
# source venv/bin/activate
# pip install -r requirements.txt

# activate virtual environment
source venv/bin/activate

# run the programme
python3 main.py

# deactivate virtual environment
deactivate venv
