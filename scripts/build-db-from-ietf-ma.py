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
import concurrent.futures
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
from itertools     import repeat
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

# FIXME: not currently used
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


# FIXME: not currently used
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

# FIXME: not currently used
def fix_name(old_name: Optional[str]) -> Optional[str]:
    if old_name is None:
        return None

    name = old_name.strip("'\" ")

    if name.endswith(" via Datatracker"):
        name = name[:-16]

    if name == "":
        name = None

    #if name != old_name:
    #    print(f"    rewrite {old_name} -> {name}")
    return name


# FIXME: not currently used
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
                lcomb = lcomb[1:-1]
            if lcomb.startswith('"') and lcomb.endswith('"'):
                lcomb = lcomb[1:-1]
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

    #if addr != old_addr:
    #    print(f"    rewrite {old_addr} -> {addr}")

    if addr == "":
        return None
    else:
        return addr.strip()



# FIXME: not currently used
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


# FIXME: not currently used
def is_list_owner_addr(addr, folder): 
    addr = addr.strip("<>")
    if addr == "noreply@ietf.org":
        return True
    if addr == f"{folder}-bounces@ietf.org":
        return True
    if addr == f"{folder}-bounces@lists.ietf.org":
        return True
    if addr == "ietf-archive-request@IETF.NRI.Reston.VA.US":
        return True
    if addr == "ietf-archive-request@IETF.CNRI.Reston.VA.US":
        return True
    if addr.startswith(f"owner-{folder}"):
        return True
    if addr.startswith(f"owner-ietf-{folder}"):
        return True
    if addr.startswith(f"{folder}-admin@"):
        return True
    if addr.startswith(f"{folder}-approval@"):
        return True
    if addr.lower().startswith(f"mailer-daemon@"):
        return True
    return False


# FIXME: not currently used
def parse_addr_multiple_at(folder, uid, msg, hdr):
    hdr_name = None
    hdr_addr = None

    if msg["x-sender"] is not None and not is_list_owner_addr(msg["x-sender"], folder):
        # print(f"{folder}/{uid} multiple @ signs in addr: rewrite {msg['from']} -> {msg['x-sender']} (x-sender)")
        hdr_name, hdr_addr = parse_addr(msg["x-sender"])
    elif msg["x-orig-sender"] is not None and not is_list_owner_addr(msg["x-orig-sender"], folder):
        # print(f"{folder}/{uid} multiple @ signs in addr: rewrite {msg['from']} -> {msg['x-orig-sender']} (x-orig-sender)")
        hdr_name, hdr_addr = parse_addr(msg["x-orig-sender"])
    elif msg["sender"] is not None and not is_list_owner_addr(msg["sender"], folder):
        # print(f"{folder}/{uid} multiple @ signs in addr: rewrite {msg['from']} -> {msg['sender']} (sender)")
        hdr_name, hdr_addr = parse_addr(msg["sender"])
    elif msg["return-path"] is not None and not is_list_owner_addr(msg["return-path"], folder):
        # print(f"{folder}/{uid} multiple @ signs in addr: rewrite {msg['from']} -> {msg['return-path']} (return-path)")
        hdr_name, hdr_addr = parse_addr(msg["return-path"])
    else:
        hdr_from = re.sub(r"([^,]+), (.*)", r'"\1"', hdr["from"])
        # print(f"{folder}/{uid} multiple @ signs in addr: rewrite {msg['from']} -> {hdr_from} (fallback)")
        hdr_name, hdr_addr = parse_addr(hdr_from)

        if hdr_addr == "noreply@ietf.org" and "@" in hdr_name:
            hdr_addr = hdr_name
            hdr_name = ""
    return hdr_name, hdr_addr


# =============================================================================

def header_reader(sourcelines):
    name, value = sourcelines[0].split(':', 1)
    value = ''.join((value, *sourcelines[1:])).lstrip(' \t\r\n')
    value = value.rstrip('\r\n')

    if name.lower() == "to" or name.lower() == "cc":
        value = value.replace("\r\n", "")
        patterns_to_replace = [
            # Many messages sent to ietf-announce have malformed "To:" and "Cc:" headers,
            # some of which are so corrupt that they make the Python email package throw
            # an exception ('Group' object has no attribute 'local_part').  Rewrite such
            # headers to use the canonical ietf-announce@ietf.org list address.
            (r'("IETF-Announce:; ; ; ; ; @tis.com"@tis.com[; ]+ , )(.*)', r'ietf-announce@ietf.org, \2'), 
            (r'(.*)(IETF-Announce:[ ;,]+[a-zA-Z\.@:;-]+$)', r'\1ietf-announce@ietf.org'),
            (r'(.*)(IETF-Announce:(; )+[; a-z\.@\r\n]+)',   r'\1ietf-announce@ietf.org'),
            (r'(.*)(<"?IETF-Announce:"?)([a-z0-9\.@;"]+)?(>)(, @tislabs.com@tislabs.com)?(.*)',  r'\1<ietf-announce@ietf.org>\6'),
            (r'IETF-Announce: ;, tis.com@CNRI.Reston.VA.US, tis.com@magellan.tis.com',           r'ietf-announce@ietf.org'),
            (r'IETF-Announce: ;, "localhost.MIT.EDU": cclark@ietf.org;',                         r'ietf-announce@ietf.org'),
            (r'IETF-Announce: @IETF.CNRI.Reston.VA.US:;, IETF.CNRI.Reston.VA.US@isi.edu',        r'ietf-announce@ietf.org'),
            (r'IETF-Announce <IETF-Announce:@auemlsrv.firewall.lucent.com;>',                    r'ietf-announce@ietf.org'),
            (r'IETF-Announce: ;,  "CNRI.Reston.VA.US" <@sun.com:CNRI.Reston.VA.US@eng.sun.com>', r'ietf-announce@ietf.org'),
            (r'IETF-Announce: ;,  "neptune.tis.com" <@tis.com, @baynetworks.com:neptune.tis.com@baynetworks.com>, tis.com@tis.com', r'ietf-announce@ietf.org'),
            (r'IETF-Announce: "IETF-Announce:;@IETF.CNRI.Reston.VA.US@PacBell.COM" <>;,  IETF.CNRI.Reston.VA.US@pacbell.com', r'ietf-announce@ietf.org'),
            (r'IETF-Announce: %IETF.CNRI.Reston.VA.US@tgv.com;',  r'ietf-announce@ietf.org'),
            (r'(IETF-Announce: ; ; ; , )(@pa.dec.com[ ;,]+)+',    r'ietf-announce@ietf.org'), 
            (r'IETF-Announce:;;;@gis.net;',              r'ietf-announce@ietf.org'),
            (r'IETF-Announce:;;@gis.net',                r'ietf-announce@ietf.org'),
            (r'IETF-Announce:@ietf.org, ;;;@ietf.org;',  r'ietf-announce@ietf.org'),
            (r'IETF-Announce:@cisco.com, ";"@cisco.com', r'ietf-announce@ietf.org'),
            (r'IETF-Announce:, ";"@cisco.com',           r'ietf-announce@ietf.org'),
            (r'IETF-Announce:@cisco.com',                r'ietf-announce@ietf.org'),
            (r'"IETF-Announce:"@netcentrex.net',         r'ietf-announce@ietf.org'),
            (r'IETF-Announce:@above.proper.com',         r'ietf-announce@ietf.org'),
            (r'IETF-Announce:all-ietf@ietf.org',         r'ietf-announce@ietf.org'),
            (r'i IETF-Announce: ;',                      r'ietf-announce@ietf.org'),
            (r'IETF-Announce: ;',                        r'ietf-announce@ietf.org'),
            (r'IETF-Announce:;',                         r'ietf-announce@ietf.org'),
            (r'IETF-Announce:',                          r'ietf-announce@ietf.org'),
            # Rewrite variants of "undisclosed-recipients; ;" into a consistent form:
            (r'("?[Uu]ndisclosed.recipients"?: ;+)(, @[a-z\.]+)?(.*)',                        r'undisclosed-recipients: ;\3'),
            (r'(.*)(unlisted-recipients:; \(no To-header on input\))(.*)',                    r'\1undisclosed-recipients: ;\3'),
            (r'(.*)(random-recipients:;;;@cs.utk.edu; \(info-mime and ietf-822 lists\))(.*)', r'\1undisclosed-recipients: ;\3'),
            (r'(.*)("[A-Za-z\.]+":;+@tislabs.com;;;)(.*)',                                    r'\1undisclosed-recipients: ;\3'),
            (r'undisclosed-recipients:;;:;',                                                  r'undisclosed-recipients: ;'),
            # Rewrite other problematic headers:
            (r'(moore@cs.utk.edu)?(, )?(authors:;+@cs.utk.edu;+)(.*)', r'\1\4'),
            (r'(RFC 3023 authors: ;)',                                 r'mmurata@trl.ibm.co.jp, simonstl@simonstl.com, dan@dankohn.com'),
            (r'=\?ISO-8859-1\?B\?QWJhcmJhbmVsLA0KICAgIEJlbmphbWlu\?=', r'Benjamin Abarbanel'),
            (r'=\?ISO-8859-15\?B\?UGV0ZXJzb24sDQogICAgSm9u\?=',        r'Jon Peterson'),
        ]
        for (pattern, replacement) in patterns_to_replace:
            new_value = re.sub(pattern, replacement, value)
            if new_value != value:
                # print(f"header_reader: [{value}] -> [{new_value}]")
                value = new_value
                break

    return (name, value)


def parse_hdr_from(uid, msg):
    hdr = msg["from"]
    if hdr is None:
        # The "From:" header is missing
        return (None, None)
    else:
        addr_list = getaddresses([hdr])
        if len(addr_list) == 0:
            # The "From:" header is present but empty
            from_name = None
            from_addr = None
        elif len(addr_list) == 1:
            # The "From:" header contains a single well-formed address.
            from_name, from_addr = addr_list[0]
        elif len(addr_list) > 1:
            # The "From:" header contains multiple well-formed addresses; use the first one with a valid domain.
            from_name = None
            from_addr = None
            for group in hdr.groups:
                if   len(group.addresses) == 0:
                    pass
                elif len(group.addresses) == 1:
                    if "." in group.addresses[0].domain: # We consider the domain to be valid if it contains a "."
                        from_name = group.addresses[0].display_name
                        from_addr = group.addresses[0].addr_spec
                        break
                else:
                    raise RuntimeError(f"Cannot parse \"From:\" header: uid={uid} - multiple addresses in group")
            # print(f"parse_hdr_from: ({uid}) multiple addresses [{hdr}] -> [{from_name}],[{from_addr}]")
        else:
            raise RuntimeError(f"Cannot parse \"From:\" header: uid={uid} cannot happen")
            sys.exit(1)

        if from_addr == "":
           from_addr = None

        if from_name == "":
            from_name = None

        return (from_name, from_addr)


def parse_hdr_to_cc(uid, msg, to_cc):
    try:
        hdr = msg[to_cc]
        if hdr is None:
            return []
        else:
            try:
                headers = []
                for name, addr in getaddresses([hdr]):
                    headers.append((name, addr))
                return headers
            except:
                print(f"failed: parse_hdr_to_cc (uid: {uid}) {hdr}")
                return []
    except Exception as e: 
        print(f"failed: parse_hdr_to_cc (uid: {uid}) cannot extract {to_cc} header")
        print(f"  {e}")
        return []


def parse_hdr_subject(uid, msg):
    hdr = msg["subject"]
    if hdr is None:
        return None
    else:
        return hdr.strip()


def parse_hdr_date(uid, msg):
    if msg["date"] is None:
        return None
    hdr = msg["date"].strip()

    try:
        # Standard date format:
        temp = parsedate_to_datetime(hdr)
        date = temp.astimezone(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
        return date
    except:
        try:
            # Standard format, with invalid timezone: Mon, 27 Dec 1993 13:46:36 +22306256
            # Parse assuming the timezone is UTC
            split = hdr.split(" ")[:-1]
            split.append("+0000")
            joined = " ".join(split)
            date = parsedate_to_datetime(joined).astimezone(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
            # print(f"parse_hdr_date: okay (1): {date} | {hdr}")
            return date
        except:
            try:
                # Non-standard date format: 04-Jan-93 13:22:13 (assume UTC timezone)
                temp = datetime.datetime.strptime(hdr, "%d-%b-%y %H:%M:%S")
                date = temp.astimezone(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
                # print(f"parse_hdr_date: okay (2): {date} | {hdr}")
                return date
            except:
                try:
                    # Non-standard date format: 30-Nov-93 17:23 (assume UTC timezone)
                    temp = datetime.datetime.strptime(hdr, "%d-%b-%y %H:%M")
                    date = temp.astimezone(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
                    # print(f"parse_hdr_date: okay (3): {date} | {hdr}")
                    return date
                except:
                    try:
                        # Non-standard date format: 2006-07-29 00:55:01 (assume UTC timezone)
                        temp = datetime.datetime.strptime(hdr, "%Y-%m-%d %H:%M:%S")
                        date = temp.astimezone(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
                        # print(f"parse_hdr_date: okay (4): {date} | {hdr}")
                        return date
                    except:
                        try:
                            # Non-standard date format: Mon, 17 Apr 2006  8: 9: 2 +0300
                            tmp1 = hdr.replace(": ", ":0").replace("  ", " 0")
                            tmp2 = parsedate_to_datetime(tmp1)
                            date = tmp2.astimezone(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S")
                            # print(f"parse_hdr_date: okay (5): {date} | {hdr}")
                            return date

                        except:
                            # print(f"failed: parse_hdr_date (uid: {uid}) {hdr}")
                            return None


def parse_hdr_message_id(uid, msg):
    hdr = msg["message-id"]
    if hdr is None:
        return None
    else:
        return hdr.strip()


def parse_hdr_in_reply_to(uid, msg):
    hdr = msg["in-reply-to"]
    if hdr is not None and hdr != "":
        return hdr.strip()
    hdr = msg["references"]
    if hdr is not None and hdr != "":
        return hdr.strip().split(" ")[-1]
    return None


def parse_message(data):
    parsing_policy = policy.default.clone(header_source_parse = header_reader)

    uid = data["uid"]
    raw = base64.b64decode(data["msg"])
    msg = BytesHeaderParser(policy=parsing_policy).parsebytes(raw)

    from_name, from_addr = parse_hdr_from(uid, msg)

    msg = {
            "uid"         : uid,
            "from_name"   : from_name,
            "from_addr"   : from_addr,
            "to"          : parse_hdr_to_cc(uid, msg, "to"),
            "cc"          : parse_hdr_to_cc(uid, msg, "cc"),
            "subject"     : parse_hdr_subject(uid, msg),
            "date"        : parse_hdr_date(uid, msg),
            "message_id"  : parse_hdr_message_id(uid, msg),
            "in_reply_to" : parse_hdr_in_reply_to(uid, msg),
            "raw_data"    : raw
          }

    return msg


# =============================================================================
# Main code follows:

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <lists.json> <ietf-ma.sqlite>")
        sys.exit(1)

    ma_file = Path(sys.argv[1])
    db_file = Path(sys.argv[2])

    with open(ma_file, "r") as inf:
        ma_json = json.load(inf)

    db_temp = db_file.with_suffix(".tmp")
    db_temp.unlink(missing_ok=True)

    db_connection = sqlite3.connect(db_temp)
    db_connection.execute("pragma journal_mode = WAL;")
    db_connection.execute("pragma synchronous = normal;")

    create_tables(db_connection)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        for folder in ma_json["folders"]:
            print(f"  {folder}")

            msg_count = 0
            first_date = "2038-01-19 03:14:07"
            final_date = "1970-01-01 00:00:00"

            folder_path = Path("downloads/ietf-ma/lists") / f"{folder}.json"
            with open(folder_path, "r") as inf:
                meta = json.load(inf)

            for msg in executor.map(parse_message, meta["msgs"], chunksize=16):
                msg_count += 1

                db_cursor = db_connection.cursor()

                val = (None, 
                       meta["folder"],
                       meta["uidvalidity"],
                       msg["uid"],
                       msg["from_name"],
                       msg["from_addr"],
                       msg["subject"],
                       msg["date"],
                       msg["message_id"],
                       msg["in_reply_to"],
                       msg["raw_data"])
                sql = f"INSERT INTO ietf_ma_messages VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING message_num"
                num = db_cursor.execute(sql, val).fetchone()[0]

                for name, addr in msg["to"]:
                    sql = f"INSERT INTO ietf_ma_messages_to VALUES (?, ?, ?, ?)"
                    db_cursor.execute(sql, (None, num, name, addr))

                for name, addr in msg["cc"]:
                    sql = f"INSERT INTO ietf_ma_messages_cc VALUES (?, ?, ?, ?)"
                    db_cursor.execute(sql, (None, num, name, addr))

                if msg["date"] is not None and msg["date"] > final_date:
                    final_date = msg["date"]
                if msg["date"] is not None and msg["date"] < first_date:
                    first_date = msg["date"]

            val = (folder, msg_count, first_date, final_date)
            sql = f"INSERT INTO ietf_ma_lists VALUES (?, ?, ?, ?)"
            db_cursor.execute(sql, val)

            db_connection.commit()

    db_connection.execute('VACUUM;') 
    db_temp.rename(db_file)

