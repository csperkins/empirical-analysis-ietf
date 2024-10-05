#!/usr/bin/env python3
#
# Copyright (c) 2024 University of Glasgow
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
#2. Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import json
import os
import requests
import sys

from typing import Any, Dict, Iterator


def fetch_multi(session, dt_url, uri) -> Iterator[Dict[Any, Any]]:
    while uri is not None:
        r = session.get(f"{dt_url}{uri}")
        if r.status_code == 200:
            meta = r.json()['meta']
            objs = r.json()['objects']
            for obj in objs:
                yield obj
            uri = meta["next"]
        else:
            print(f"Cannot fetch: {r.status_code}")
            sys.exit(1)


if len(sys.argv) != 3 and len(sys.argv) != 4:
    print(f"Usage: {sys.argv[0]} <prefix> [<order_by>] <output_file>")
    sys.exit(1)

if len(sys.argv) == 3:
    prefix    = sys.argv[1]
    out_file  = sys.argv[2]
    query_uri = f"{prefix}"
else:
    prefix    = sys.argv[1]
    order_by  = sys.argv[2]
    out_file  = sys.argv[3]
    query_uri = f"{prefix}?order_by={order_by}"

dt_url    = os.environ.get("IETFDATA_DT_URL", "https://datatracker.ietf.org/")
session   = requests.Session()

results   = []

for item in fetch_multi(session, dt_url, query_uri):
    print(f"   {item['resource_uri']}")
    results.append(item)

print(f"   Write {out_file}")
with open(out_file, "w") as outf:
    json.dump(results, outf, indent=3)
print(f"   Done.")

