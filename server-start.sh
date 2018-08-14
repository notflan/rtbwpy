#!/bin/bash

rm ./rtbw.sock
rm ./buffer.dat

python3 rtbw.py --daemon rtbw.sock bant 10
