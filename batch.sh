#!/bin/bash

while read p; do
  ./migrate.py $p
done < projects.txt
