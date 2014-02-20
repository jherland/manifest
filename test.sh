#!/bin/sh

mydir=$(dirname $0)

for python in $(ls /usr/bin/python?.?); do
    echo "Running test.py under ${python}:"
    ${python} ${mydir}/test.py || exit 1
done
