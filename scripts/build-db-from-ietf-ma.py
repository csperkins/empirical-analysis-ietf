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
import pprint
import sqlite3
import sys

from dataclasses   import dataclass
from email         import policy, utils
from email.parser  import BytesParser
from email.message import Message
from email.utils   import parseaddr, parsedate_to_datetime, getaddresses
from typing        import Any, Dict, List, Optional
from pathlib       import Path

# =============================================================================
# Helper function to create database tables

def create_tables(db_connection):
    db_cursor = db_connection.cursor()

    sql =  f"CREATE TABLE ietf_ma_messages (\n"
    sql += f"  message_num    INTEGER PRIMARY KEY AUTOINCREMENT,\n"
    sql += f"  mailing_list   TEXT NOT NULL,\n"
    sql += f"  uidvalidity    INTEGER NOT NULL,\n"
    sql += f"  uid            INTEGER NOT NULL,\n"
    sql += f"  from_name      TEXT,\n"
    sql += f"  from_addr      TEXT,\n"
    sql += f"  subject        TEXT,\n"
    sql += f"  date           TEXT,\n"
    sql += f"  date_unparsed  TEXT,\n"
    sql += f"  message_id     TEXT,\n"
    sql += f"  in_reply_to    TEXT,\n"
    sql += f"  message        BLOB,\n"
    sql += f"  FOREIGN KEY (mailing_list) REFERENCES ietf_ma_lists (name)\n"
    sql += ");\n"
    db_cursor.execute(sql)

    sql = f"CREATE INDEX index_ietf_ma_messages_from_addr   ON ietf_ma_messages(from_addr);\n"
    db_cursor.execute(sql)
    sql = f"CREATE INDEX index_ietf_ma_messages_message_id  ON ietf_ma_messages(message_id);\n"
    db_cursor.execute(sql)
    sql = f"CREATE INDEX index_ietf_ma_messages_in_reply_to ON ietf_ma_messages(in_reply_to);\n"
    db_cursor.execute(sql)


    sql =  f"CREATE TABLE ietf_ma_messages_to (\n"
    sql += f"  id          INTEGER PRIMARY KEY AUTOINCREMENT,\n"
    sql += f"  message_num INTEGER,\n"
    sql += f"  to_name     TEXT,\n"
    sql += f"  to_addr     TEXT,\n"
    sql += f"  FOREIGN KEY (message_num) REFERENCES ietf_ma_messages (message_num)\n"
    sql += ");\n"
    db_cursor.execute(sql)


    sql =  f"CREATE TABLE ietf_ma_messages_cc (\n"
    sql += f"  id          INTEGER PRIMARY KEY AUTOINCREMENT,\n"
    sql += f"  message_num INTEGER,\n"
    sql += f"  cc_name     TEXT,\n"
    sql += f"  cc_addr     TEXT,\n"
    sql += f"  FOREIGN KEY (message_num) REFERENCES ietf_ma_messages (message_num)\n"
    sql += ");\n"
    db_cursor.execute(sql)

    sql =  f"CREATE TABLE ietf_ma_lists (\n"
    sql += f"  name       TEXT NOT NULL PRIMARY KEY,\n"
    sql += f"  msg_count  INTEGER,\n"
    sql += f"  first_date TEXT,\n"
    sql += f"  last_date  TEXT\n"
    sql += ");\n"
    db_cursor.execute(sql)

    db_connection.commit()


# =============================================================================
# Helper function to populate database

def fixaddr(old_addr) -> str:
    addr = old_addr

    if addr is None:
        return None

    # Rewrite, e.g., arnaud.taddei=40broadcom.com@dmarc.ietf.org to arnaud.taddei@broadcom.com
    if addr.endswith("@dmarc.ietf.org"):
        addr = addr[:-15].replace("=40", "@")

    # Rewrite, e.g., "Michelle Claudé <Michelle.Claude@prism.uvsq.fr>"@prism.uvsq.fr to Michelle.Claude@prism.uvsq.fr
    # or "minshall@wc.novell.com"@decpa.enet.dec.com to minshall@wc.novell.com
    if addr.count("@") == 2:
        lpart = addr.split("@")[0]
        cpart = addr.split("@")[1]
        rpart = addr.split("@")[2]
        if lpart.startswith('"') and cpart.endswith('"'):
            lcomb = f"{lpart}@{cpart}"
            if lcomb.startswith("'") and lcomb.endswith("'"):
                lcomb = addr[1:-1]
            if lcomb.startswith('"') and lcomb.endswith('"'):
                lcomb = addr[1:-1]
            lname, laddr = parseaddr(lcomb)
            if laddr != '':
                addr = laddr

    # Rewrite, e.g., lear at cisco.com to lear@cisco.com
    if " at " in addr:
        addr = addr.replace(" at ", "@")

    # Strip leading and trailing '
    if addr.startswith("'") and addr.endswith("'"):
        addr = addr[1:-1]

    # Strip leading and trailing "
    if addr.startswith('"') and addr.endswith('"'):
        addr = addr[1:-1]

    #if addr != old_addr:
    #    print(f"          {old_addr} -> {addr}")
    return addr.strip()



def populate_data(db_connection, folder):
    print(f"  {folder}")

    db_cursor = db_connection.cursor()

    folder_path = Path("downloads/ietf-ma/lists") / f"{folder}.json"
    with open(folder_path, "r") as inf:
        meta = json.load(inf)

    msg_count = 0
    first_date = "2038-01-19 03:14:07"
    final_date = "1970-01-01 00:00:00"

    for data in meta["msgs"]:
        msg_count += 1

        raw = base64.b64decode(data["msg"])
        msg = BytesParser(policy=policy.default).parsebytes(raw)

        uid             = data["uid"]
        uidvalidity     = int(meta["uidvalidity"])
        hdr_from_name   = None
        hdr_from_addr   = None
        hdr_subject     = None
        hdr_date        = None
        hdr_message_id  = None
        hdr_in_reply_to = None
        parsed_date     = None

        try:
            hdr_from        = msg["from"]
            hdr_from_name, hdr_from_addr = parseaddr(hdr_from)
            hdr_subject     = msg["subject"]
            hdr_date        = msg["date"]
            hdr_message_id  = msg["message-id"]
            in_reply_to = msg["in-reply-to"]
            references  = msg["references"]
            if in_reply_to != "":
                hdr_in_reply_to = in_reply_to
            elif references != "":
                hdr_in_reply_to = references.strip().split(" ")[-1]
            parsed_date = parsedate_to_datetime(hdr_date).astimezone(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
        except:
            print(f"    cannot parse headers for {folder}/{uid}")
        val = (None,
               folder,
               uidvalidity,
               uid,
               hdr_from_name,
               fixaddr(hdr_from_addr),
               hdr_subject,
               parsed_date,
               hdr_date,
               hdr_message_id,
               hdr_in_reply_to,
               raw)
        sql = f"INSERT INTO ietf_ma_messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING message_num"
        num = db_cursor.execute(sql, val).fetchone()[0]

        try:
            if msg["to"] is not None:
                try:
                    for to_name, to_addr in getaddresses([msg["to"]]):
                        sql = f"INSERT INTO ietf_ma_messages_to VALUES (?, ?, ?, ?)"
                        db_cursor.execute(sql, (None, num, to_name, fixaddr(to_addr)))
                except:
                    print(f"    cannot parse \"To:\" header for {folder}/{uid}")
        except:
            print(f"    malformed \"To:\" header for {folder}/{uid}")

        try:
            if msg["cc"] is not None:
                try:
                    for cc_name, cc_addr in getaddresses([msg["cc"]]):
                        sql = f"INSERT INTO ietf_ma_messages_cc VALUES (?, ?, ?, ?)"
                        db_cursor.execute(sql, (None, num, cc_name, fixaddr(cc_addr)))
                except:
                    print(f"    cannot parse \"Cc:\" header for {folder}/{uid}")
        except:
            print(f"    malformed \"Cc:\" header for {folder}/{uid}")


        if parsed_date is not None and parsed_date > final_date:
            final_date = parsed_date
        if parsed_date is not None and parsed_date < first_date:
            first_date = parsed_date

    db_connection.commit()

    # FIXME: can this be a virtual table calculated by the database?
    val = (folder, msg_count, first_date, final_date)
    sql = f"INSERT INTO ietf_ma_lists VALUES (?, ?, ?, ?)"
    db_cursor.execute(sql, val)
    db_connection.commit()


# =============================================================================
# Main code follows:

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <list.json> <output.sqlite>")
    sys.exit(1)

ma_file = Path(sys.argv[1])
db_file = Path(sys.argv[2])
db_temp = db_file.with_suffix(".tmp")

with open(ma_file, "r") as inf:
    ma_json = json.load(inf)

db_temp.unlink(missing_ok=True)
db_connection = sqlite3.connect(db_temp)

create_tables(db_connection)

db_connection.execute('VACUUM;') 

for folder in ma_json["folders"]:
    populate_data(db_connection, folder)

db_temp.rename(db_file)

