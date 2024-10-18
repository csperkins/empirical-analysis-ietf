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

import datetime
import json
import os
import requests
import sys

from dataclasses import dataclass
from typing      import Any, Dict, List, Optional

# =============================================================================

DTSchema = Dict[str,Any]
DTObject = Dict[str,Any]

class DTData:
    def __init__(self) -> None:
        self.prefixes : List[str] = []
        self.schemas  : Dict[str,DTSchema] = {}
        self.objects  : Dict[str,List[DTObject]] = {}


    def load(self, json_path: str) -> None:
        with open(json_path, "r") as inf:
            data = json.load(inf)
        if data['prefix'] in self.prefixes:
            print(f"ERROR: duplicate prefix {data['prefix']}")
            sys.exit(1)
        self.prefixes.append(data['prefix'])
        self.schemas[data['prefix']] = data['schema']
        self.objects[data['prefix']] = data['objects']
        print(f"{len(self.prefixes):3} {len(data['objects']):8} {data['prefix']}")


    def has_prefix(self, prefix: str) -> bool:
        return prefix in self.prefixes


# =============================================================================
# Main code follows:

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} [dt_json_files...] <output_file>")
    sys.exit(1)

out_path = sys.argv[-1]

dt = DTData()
for infile in sys.argv[1:-1]:
    dt.load(infile)

# vim: set ts=4 sw=4 tw=0 ai:
