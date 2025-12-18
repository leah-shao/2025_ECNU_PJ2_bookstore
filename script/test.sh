#!/bin/sh
export PATHONPATH=`pwd`
coverage erase
coverage run --timid --branch --source fe,be --concurrency=thread -m pytest -v --ignore=fe/data
coverage report
coverage html