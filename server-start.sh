#!/bin/bash

rm ./rtbw.sock
rm ./buffer.dat

python3 rtbw.py --daemon rtbw.sock $(cat conf/board) $(cat conf/time)
