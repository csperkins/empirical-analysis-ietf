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
import json
import os
import pprint
import sys
import sqlite3

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <ietf-ma.sqlite> <outfile.json>")
    sys.exit(1)

db_path  = sys.argv[1]
out_path = sys.argv[2]

db_connection = sqlite3.connect(db_path)
db_cursor = db_connection.cursor()

with open(out_path, "w") as outf:
    print("Dumping messages:   ", end="")
    num  = 0
    sql  = "SELECT message_num, mailing_list, uidvalidity, uid,"
    sql += "       from_name, from_addr, subject, date, message_id, in_reply_to "
    sql += "FROM ietf_ma_messages;"
    for values in db_cursor.execute(sql):
        print(values, file=outf)
        if num % 50000 == 0:
            print(".", end="", flush=True)
        num += 1
    print("")

    print("Dumping message to: ", end="")
    num  = 0
    sql  = "SELECT id, message_num, to_name, to_addr FROM ietf_ma_messages_to;"
    for values in db_cursor.execute(sql):
        print(values, file=outf)
        if num % 50000 == 0:
            print(".", end="", flush=True)
        num += 1
    print("")

    print("Dumping message cc: ", end="")
    num  = 0
    sql  = "SELECT id, message_num, cc_name, cc_addr FROM ietf_ma_messages_cc;"
    for values in db_cursor.execute(sql):
        print(values, file=outf)
        if num % 50000 == 0:
            print(".", end="", flush=True)
        num += 1
    print("")

