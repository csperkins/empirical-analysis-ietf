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
import re
import sqlite3
import sys

from dataclasses   import dataclass
from email         import policy, utils
from email.parser  import BytesHeaderParser
from email.message import Message
from email.utils   import parseaddr, parsedate_to_datetime, getaddresses, unquote
from typing        import Any, Dict, List, Optional, Tuple
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
    sql += f"  message_id     TEXT,\n"
    sql += f"  in_reply_to    TEXT,\n"
    sql += f"  message        BLOB,\n"
    sql += f"  FOREIGN KEY (mailing_list) REFERENCES ietf_ma_lists (name)\n"
    sql += ");\n"
    db_cursor.execute(sql)

    sql = f"CREATE INDEX index_ietf_ma_messages_mailing_list ON ietf_ma_messages(mailing_list);\n"
    db_cursor.execute(sql)
    sql = f"CREATE INDEX index_ietf_ma_messages_from_addr    ON ietf_ma_messages(from_addr);\n"
    db_cursor.execute(sql)
    sql = f"CREATE INDEX index_ietf_ma_messages_date         ON ietf_ma_messages(date);\n"
    db_cursor.execute(sql)
    sql = f"CREATE INDEX index_ietf_ma_messages_subject      ON ietf_ma_messages(subject);\n"
    db_cursor.execute(sql)
    sql = f"CREATE INDEX index_ietf_ma_messages_message_id   ON ietf_ma_messages(message_id);\n"
    db_cursor.execute(sql)
    sql = f"CREATE INDEX index_ietf_ma_messages_in_reply_to  ON ietf_ma_messages(in_reply_to);\n"
    db_cursor.execute(sql)

    sql =  f"CREATE TABLE ietf_ma_messages_to (\n"
    sql += f"  id          INTEGER PRIMARY KEY AUTOINCREMENT,\n"
    sql += f"  message_num INTEGER,\n"
    sql += f"  to_name     TEXT,\n"
    sql += f"  to_addr     TEXT,\n"
    sql += f"  FOREIGN KEY (message_num) REFERENCES ietf_ma_messages (message_num)\n"
    sql += ");\n"
    db_cursor.execute(sql)

    sql = f"CREATE INDEX index_ietf_ma_messages_to_message_num ON ietf_ma_messages_to(message_num);\n"
    db_cursor.execute(sql)
    sql = f"CREATE INDEX index_ietf_ma_messages_to_to_addr     ON ietf_ma_messages_to(to_addr);\n"
    db_cursor.execute(sql)

    sql =  f"CREATE TABLE ietf_ma_messages_cc (\n"
    sql += f"  id          INTEGER PRIMARY KEY AUTOINCREMENT,\n"
    sql += f"  message_num INTEGER,\n"
    sql += f"  cc_name     TEXT,\n"
    sql += f"  cc_addr     TEXT,\n"
    sql += f"  FOREIGN KEY (message_num) REFERENCES ietf_ma_messages (message_num)\n"
    sql += ");\n"
    db_cursor.execute(sql)

    sql = f"CREATE INDEX index_ietf_ma_messages_cc_message_num ON ietf_ma_messages_cc(message_num);\n"
    db_cursor.execute(sql)
    sql = f"CREATE INDEX index_ietf_ma_messages_cc_cc_addr     ON ietf_ma_messages_cc(cc_addr);\n"
    db_cursor.execute(sql)

    sql =  f"CREATE TABLE ietf_ma_lists (\n"
    sql += f"  name       TEXT NOT NULL PRIMARY KEY,\n"
    sql += f"  msg_count  INTEGER,\n"
    sql += f"  first_date TEXT,\n"
    sql += f"  last_date  TEXT\n"
    sql += ");\n"
    db_cursor.execute(sql)

    sql = f"CREATE INDEX index_ietf_ma_lists_name ON ietf_ma_lists(name);\n"
    db_cursor.execute(sql)

    db_connection.commit()


# =============================================================================
# Helper function to parse To: and Cc: headers

def fix_to_cc1(folder, uid, old_tocc) -> Optional[str]:
    if old_tocc is None:
        return None

    tocc = old_tocc

    if tocc.count('\\"') == 1:
        tocc = tocc.replace('\\"', '')

    if tocc.startswith('"') and tocc.endswith('"') and tocc.count('"') == 2:
        tocc = tocc[1:-1]

    if tocc.count("@") == 0 and tocc.count(" at ") == 1:
        tocc = tocc.replace(" at ", "@")

    if tocc != old_tocc:
        print(f"    {folder}/{uid} rewrite(1) {old_tocc} -> {tocc}")
    return tocc


def fix_to_cc2(folder, uid, old_name, old_addr):
    new_name = old_name
    new_addr = old_addr

    if new_addr.count("@") == 0 and new_addr.count(" at ") == 1:
        new_addr = new_addr.replace(" at ", "@")

    name, addr = parseaddr(new_addr)
    if name is not None and addr != new_addr:
        new_name = name
        new_addr = addr

    if new_name != old_name or new_addr != old_addr:
        print(f"    {folder}/{uid} rewrite(2) [{old_name},{old_addr}] -> [{new_name},{new_addr}]")
    return new_name, new_addr

    
# =============================================================================
# Helper functions to parse From: header and addresses

def fix_name(old_name: Optional[str]) -> Optional[str]:
    if old_name is None:
        return None

    name = old_name.strip("'\" ")

    if name.endswith(" via Datatracker"):
        name = name[:-16]

    #if name != old_name:
    #    print(f"    rewrite {old_name} -> {name}")
    return name


def fix_addr(old_addr: Optional[str]) -> Optional[str]:
    if old_addr is None:
        return None

    addr = old_addr.lower()

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

    # Strip leading and trailing characters
    addr = addr.lstrip("\"'<")
    addr = addr.rstrip("\"'>")

    # Strip trailing .RemoveThisWord
    if addr.endswith(".RemoveThisWord"):
        addr = addr[:-15]

    # Remove, e.g., " on behalf of Behcet Sarikaya" from addresses
    if " on behalf of " in addr:
        addr = addr[:addr.find(" on behalf of ")]

    # FIXME other possible malformed addresses:
    #   aqm@ietf.org <aqm@ietf.org>

    #if addr != old_addr:
    #    print(f"    rewrite {old_addr} -> {addr}")
    return addr.strip()


def parse_addr(unparsed_addr: Optional[str]) -> Tuple[str, str]:
    if unparsed_addr is None:
        return None, None
    try:
        orig_name, orig_addr = parseaddr(unparsed_addr)
        name = fix_name(orig_name)
        addr = fix_addr(orig_addr)
        return name, addr
    except:
        print(f"    cannot parse address: {unparsed_addr}")
        sys.exit(1)


# =============================================================================
# Helpful function to parse an email message:

def parse_headers_core(folder, uid, msg, hdr):
    try:
        hdr["from"]        = msg["from"]
        hdr["from_name"], hdr["from_addr"] = parse_addr(hdr["from"])
        hdr["subject"]     = msg["subject"]
        hdr["date"]        = msg["date"]
        hdr["message_id"]  = msg["message-id"]
    except:
        print(f"    cannot parse message {folder}/{uid}: core headers")


def parse_headers_reply(folder, uid, msg, hdr):
    try:
        in_reply_to = msg["in-reply-to"]
        references  = msg["references"]
        if in_reply_to != "":
            hdr["in_reply_to"] = in_reply_to
        elif references != "":
            hdr["in_reply_to"] = references.strip().split(" ")[-1]
    except:
        print(f"    cannot parse message {folder}/{uid}: in_reply_to/references")


def parse_headers_date(folder, uid, msg, hdr):
    try:
        hdr["date"] = parsedate_to_datetime(msg["date"]).astimezone(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
    except:
        print(f"    cannot parse message {folder}/{uid}: date")


def parse_headers_to_cc(folder, uid, msg, hdr, to_cc):
    try:
        if msg[to_cc] is not None:
            try:
                for name, addr in getaddresses([fix_to_cc1(folder, uid, msg[to_cc])]):
                    name, addr = fix_to_cc2(folder, uid, name, addr)
                    hdr[to_cc].append((fix_name(name), fix_addr(addr)))
            except:
                print(f"    cannot parse message {folder}/{uid}: {to_cc} (1)")
    except:
        print(f"    cannot parse message {folder}/{uid}: {to_cc} (2)")


def header_reader(sourcelines):
    name, value = sourcelines[0].split(':', 1)
    old_value = ''.join((value, *sourcelines[1:])).lstrip(' \t\r\n').rstrip('\r\n')
    new_value = old_value

    # Rewrite "To": addresses of the form "IETF-Announce:;;;@grc.nasa.gov;":
    if name == "To" and new_value.startswith("IETF-Announce:;"):
        new_value = "ietf-announce@ietf.org"

    # Rewrite "To:" addresses of the form "icn-interest at listserv.netlab.nec.de":
    if name == "To" and "@" not in new_value and " at " in new_value:
        new_value = new_value.replace(" at ", "@")

    if name in ["From", "To", "Cc"]:
        # Rewrite addresses of the form:
        #   'Shihang\(Vincent\)' <shihang9=40huawei.com@dmarc.ietf.org>
        # that are incorrectly quoted and break the Python header parser.
        new_value = re.sub(r"'([A-Za-z ]+)\\\(([A-Za-z ]+)\\\)'", r'"\1(\2)"', new_value)
        # Rewritw ""Shihang (Vincent)"" -> "Shihang (Vincent)"
        new_value = re.sub(r'""([A-Za-z ]+)\(([A-Za-z ]+)\)""', r'"\1(\2)"', new_value)

    # if new_value != old_value:
    #     print(f"{name}: {old_value} ==> {new_value}")

    return (name, new_value)


def parse_message(folder, uid, uidvalidity, raw_message):
    parsing_policy = policy.default.clone(header_source_parse = header_reader)
    msg = BytesHeaderParser(policy=parsing_policy).parsebytes(raw_message)

    hdr = {
        "uid"         : uid,
        "uidvalidity" : uidvalidity,
        "from_name"   : None,
        "from_addr"   : None,
        "subject"     : None,
        "date"        : None,
        "message_id"  : None,
        "in_reply_to" : None,
        "date"        : None,
        "to"          : [],
        "cc"          : []
    }

    parse_headers_core(folder, uid, msg, hdr)
    parse_headers_date(folder, uid, msg, hdr)
    parse_headers_reply(folder, uid, msg, hdr)
    parse_headers_to_cc(folder, uid, msg, hdr, "to")
    parse_headers_to_cc(folder, uid, msg, hdr, "cc")

    return hdr


# =============================================================================
# Helper function to populate database

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

        uid         = data["uid"]
        uidvalidity = int(meta["uidvalidity"])

        raw = base64.b64decode(data["msg"])
        hdr = parse_message(folder, uid, uidvalidity, raw)

        val = (None, folder, uidvalidity, uid,
               hdr["from_name"],
               hdr["from_addr"],
               hdr["subject"],
               hdr["date"],
               hdr["message_id"],
               hdr["in_reply_to"],
               raw)
        sql = f"INSERT INTO ietf_ma_messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING message_num"
        num = db_cursor.execute(sql, val).fetchone()[0]

        for name, addr in hdr["to"]:
            sql = f"INSERT INTO ietf_ma_messages_to VALUES (?, ?, ?, ?)"
            db_cursor.execute(sql, (None, num, name, addr))

        for name, addr in hdr["cc"]:
            sql = f"INSERT INTO ietf_ma_messages_cc VALUES (?, ?, ?, ?)"
            db_cursor.execute(sql, (None, num, name, addr))

        if hdr["date"] is not None and hdr["date"] > final_date:
            final_date = hdr["date"]
        if hdr["date"] is not None and hdr["date"] < first_date:
            first_date = hdr["date"]

    db_connection.commit()

    # FIXME: can this be a virtual table calculated by the database?
    val = (folder, msg_count, first_date, final_date)
    sql = f"INSERT INTO ietf_ma_lists VALUES (?, ?, ?, ?)"
    db_cursor.execute(sql, val)
    db_connection.commit()


# =============================================================================
# Test Cases:

def load_test_message(folder, uid):
    # print(f"  Loading test message {folder}/{uid}")
    uidvalidity = 0 # Not needed for these tests
    with open(f"downloads/ietf-ma/lists/{folder}.json", "r") as inf:
        folder_data = json.load(inf)
        for msg_data in folder_data["msgs"]:
            if msg_data["uid"] == int(uid):
                raw = base64.b64decode(msg_data["msg"])
                hdr = parse_message(folder, uid, uidvalidity, raw)
    return hdr


def test_message_parsing():
    hdr = load_test_message("cats", 343)
    assert hdr["from_name"] == "weilin_wang@bjtu.edu.cn"
    assert hdr["from_addr"] == "weilin_wang@bjtu.edu.cn"
    assert hdr["to"][0] == ("Adrian Farrel", "adrian@olddog.co.uk")
    assert hdr["to"][1] == ("Shihang(Vincent)", "shihang9@huawei.com")
    assert hdr["to"][2] == ("Yao Kehan", "yaokehan@chinamobile.com")
    assert hdr["to"][3] == ("draft-wang-cats-awareness-system-for-casfc@ietf.org", "draft-wang-cats-awareness-system-for-casfc@ietf.org")
    assert hdr["to"][4] == ("draft-zhang-cats-computing-aware-sfc-usecase@ietf.org", "draft-zhang-cats-computing-aware-sfc-usecase@ietf.org")
    assert hdr["cc"][0] == ("cats@ietf.org", "cats@ietf.org")

    hdr = load_test_message("pilc", 1683)
    assert hdr["from_name"] == ""
    assert hdr["from_addr"] == "internet-drafts@ietf.org"
    assert hdr["to"][0] == ("", "ietf-announce@ietf.org")
    assert hdr["cc"][0] == ("", "pilc@grc.nasa.gov")

    hdr = load_test_message("icnrg", 1591)
    assert hdr["from_name"] == ""
    assert hdr["from_addr"] == "icn-interest-bounces@listserv.netlab.nec.de"
    assert hdr["to"][0] == ("", "icn-interest@listserv.netlab.nec.de")

# =============================================================================
# Main code follows:

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <list.json> <output.sqlite>")
    sys.exit(1)

ma_file = Path(sys.argv[1])
db_file = Path(sys.argv[2])
db_temp = db_file.with_suffix(".tmp")

test_message_parsing()

with open(ma_file, "r") as inf:
    ma_json = json.load(inf)

db_temp.unlink(missing_ok=True)
db_connection = sqlite3.connect(db_temp)

create_tables(db_connection)

db_connection.execute('VACUUM;') 

for folder in ma_json["folders"]:
    populate_data(db_connection, folder)

db_temp.rename(db_file)

