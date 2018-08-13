#!/bin/bash

rm ./rtbw.sock
rm ./buffer.dat

python3 rtbw.py --buffer buffer.dat --daemon rtbw.sock bant 10
