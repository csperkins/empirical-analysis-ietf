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

import base64
import datetime
import json
import os
import requests
import sys

from typing     import Any, Dict, Iterator
from imapclient import IMAPClient
from pathlib    import Path

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <list.json>")
    sys.exit(1)

imap = IMAPClient(host='imap.ietf.org', ssl=True, use_uid=True)
imap.login("anonymous", "anonymous")

_, _, imap_ns_shared = imap.namespace()
imap_prefix    = imap_ns_shared[0][0]
imap_separator = imap_ns_shared[0][1]

folder_name = sys.argv[1][24:-5]
folder_path = f"{imap_prefix}{folder_name}"
folder_info = imap.select_folder(folder_path, readonly=True)

results = {"fetched"     : datetime.datetime.now().isoformat(),
           "folder"      : folder_name,
           "uidvalidity" : folder_info[b'UIDVALIDITY'],
           "msgs"        : []
          }

msgs_to_fetch = imap.search(['NOT', 'DELETED'])

for i in range(0, len(msgs_to_fetch), 16):
    uid_slice = msgs_to_fetch[slice(i, i+16, 1)]
    for uid, msg in imap.fetch(uid_slice, "RFC822").items():
        if msg != {}:
            data = {"uid" : uid,
                    "msg" : base64.b64encode(msg[b"RFC822"]).decode("utf-8")
                   }
            results["msgs"].append(data)
            #print(f"   {folder_name}/{uid}")

p = Path(sys.argv[1])
t = p.with_suffix(".tmp")

t.unlink(missing_ok=True)
with open(t, "w") as outf:
    json.dump(results, outf, indent=3)
t.rename(p)

