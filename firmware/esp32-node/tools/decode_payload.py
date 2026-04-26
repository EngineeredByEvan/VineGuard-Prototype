#!/usr/bin/env python3
import argparse
import json

p = argparse.ArgumentParser()
p.add_argument("payload")
a = p.parse_args()
print(json.dumps(json.loads(a.payload), indent=2))
