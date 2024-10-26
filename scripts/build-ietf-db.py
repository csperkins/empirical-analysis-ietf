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
import pprint
import requests
import sqlite3
import sys

from dataclasses import dataclass
from typing      import Any, Dict, List, Optional

# =============================================================================

class DTData:
    def __init__(self) -> None:
        self._prefixes : List[str] = []
        self._schemas  : Dict[str,Dict[str,Any]] = {}
        self._objects  : Dict[str,List[Dict[str,Any]]] = {}
        self._parsed_schemas : Dict[str,Dict[str,Any]] = {}


    def load(self, json_path: str) -> None:
        with open(json_path, "r") as inf:
            data = json.load(inf)
        if data['prefix'] in self._prefixes:
            raise RuntimeError(f"ERROR: duplicate prefix {data['prefix']}")
        self._prefixes.append(data['prefix'])
        self._schemas[data['prefix']] = data['schema']
        self._objects[data['prefix']] = data['objects']
        print(f"{len(self._prefixes):3} {len(data['objects']):8} {data['prefix']}")


    def schema(self, prefix:str) -> Dict[str,Any]:
        if prefix in self._parsed_schemas:
            return self._parsed_schemas[prefix]
        
        if prefix not in self._schemas:
            raise RuntimeError(f"Prefix not available: {prefix}")
        schema = self._schemas[prefix]
        result : Dict[str,Any] = {
            "prefix"      : prefix,
            "table"       : "ietf_dt" + prefix.replace("/", "_")[7:-1],
            "sort_by"     : None,
            "primary_key" : None,
            "columns"     : {},
            "to_one"      : {},
            "to_many"     : {}
        }
        if "ordering" in schema:
            result["sort_by"] = schema["ordering"][0]
        if "historical" in prefix:
            result["sort_by"] = None
            print(f"Not sorting {prefix}")
        for field_name in schema["fields"]:
            column = {}
            column["name"]    = field_name
            column["type"]    = schema["fields"][field_name]["type"]
            column["unique"]  = schema["fields"][field_name]["unique"]
            column["primary"] = schema["fields"][field_name]["primary_key"]
            if column["primary"]:
                result["primary_key"] = field_name
            if column["type"] == "related":
                column["type"] = schema["fields"][field_name]["related_type"]
            result["columns"][field_name] = column

        # Find the to_one and to_many mappings:
        for item in self._objects[prefix]:
            for column in result["columns"].values():
                if column["type"] == "to_one":
                    if column["name"] not in result["to_one"]:
                        if item[column["name"]] is not None and item[column["name"]] != "":
                            to_one = {
                                "refers_to_endpoint": "/".join(item[column["name"]].split("/")[:-2]) + "/",
                                "refers_to_table": "ietf_dt_" + "_".join(item[column["name"]].split("/")[3:-2])
                            }
                            result["to_one"][column["name"]] = to_one
                if column["type"] == "to_many":
                    if column["name"] not in result["to_many"]:
                        val = item[column["name"]]
                        if item[column["name"]] is not None and item[column["name"]] != "" and len(item[column["name"]]) > 0:
                            to_many = {
                                "refers_to_endpoint": "/".join(item[column["name"]][0].split("/")[:-2]) + "/",
                                "refers_to_table": "ietf_dt_" + "_".join(item[column["name"]][0].split("/")[3:-2])
                            }
                            result["to_many"][column["name"]] = to_many
        for column in result["columns"].values():
            if column["type"] == "to_one" and not column["name"] in result["to_one"]:
                column["type"] = None
            if column["type"] == "to_many" and not column["name"] in result["to_many"]:
                column["type"] = None
        self._parsed_schemas[prefix] = result
        return result


    def has_prefix(self, prefix: str) -> bool:
        return prefix in self._prefixes


    def prefixes(self) -> List[str]:
        return self._prefixes


    def uri_col(self, prefix) -> str:
        schema = self.schema(prefix)
        if "slug" in schema["columns"]:
            return "slug"
        if "id" in schema["columns"]:
            return "id"
        if prefix == "/api/v1/person/email/":
            return "address"
        if "historical" in prefix:
            return "history_id"
        raise RuntimeError(f"Cannot identify uri_col for {prefix}")


    def sql_type_for(self, prefix, column):
        assert prefix is not None
        assert column is not None
        schema = self.schema(prefix)
        stype  = schema["columns"][column]["type"]
        if stype in ["string", "datetime", "date", "timedelta"]:
            return "TEXT"
        elif stype in ["integer", "boolen"]:
            return "INTEGER"
        else:
            raise RunetimeError(f"Cannot derive sql type for {endpoint} {column}")


    def create_db_table(self, db_cursor, prefix):
        print(f"Create table {prefix}")
        schema = self.schema(prefix)
        columns = []
        foreign = []
        for column in schema["columns"].values():
            if column["name"] == "resource_uri":
                continue
            if column['type'] in ["string", "datetime", "date", "timedelta"]:
                column_sql = f"  \"{column['name']}\" TEXT"
            elif column['type'] in ["integer", "boolean"]: 
                column_sql = f"  \"{column['name']}\" INTEGER"
            elif column['type'] == "to_one": 
                foreign_table = schema["to_one"][column["name"]]["refers_to_table"]
                foreign_endpt = schema["to_one"][column["name"]]["refers_to_endpoint"]
                foreign_col   = self.uri_col(foreign_endpt)
                if foreign_endpt in self._schemas:
                    foreign.append(f"  FOREIGN KEY (\"{column['name']}\") REFERENCES {foreign_table} (\"{foreign_col}\")")
                    column_sql  = f"  \"{column['name']}\" {self.sql_type_for(foreign_endpt, foreign_col)}"
                else:
                    # The foreign endpoint is not one we mirror. Just store the content as text.
                    # e.g., /api/v1/nomcom/nomination/ refers to /api/v1/nomcom/feedback/'
                    column['type'] = "string"
                    column_sql = f"  \"{column['name']}\" TEXT"
            elif column['type'] == "to_many": 
                foreign_table  = schema["to_many"][column["name"]]["refers_to_table"]
                foreign_endpt  = schema["to_many"][column["name"]]["refers_to_endpoint"]
                column_current = schema['table'].split('_')[-1]
                column_foreign = column['name']
                sql  = f"CREATE TABLE {schema['table']}_{column['name']} (\n"
                sql += f"  \"id\" INTEGER PRIMARY KEY,\n"
                sql += f"  \"{column_current}\" {self.sql_type_for(prefix, self.uri_col(prefix))},\n"
                sql += f"  \"{column_foreign}\" {self.sql_type_for(foreign_endpt, self.uri_col(foreign_endpt))},\n"
                sql += f"  FOREIGN KEY (\"{column_current}\") REFERENCES {schema['table']} ({self.uri_col(prefix)}),\n"
                sql += f"  FOREIGN KEY (\"{column_foreign}\") REFERENCES {foreign_table} ({self.uri_col(foreign_endpt)})\n"
                sql += f");\n"
                db_cursor.execute(sql)
                continue
            elif column['type'] == None:
                continue
            else:
                print(f"unknown column type {column['type']} (create_db_table)")
                sys.exit(1)

            if column["unique"]:
                column_sql += " UNIQUE"
            if column["name"] == self.uri_col(prefix):
                column_sql += " PRIMARY KEY"
            columns.append(column_sql)
        sql = f"CREATE TABLE {schema['table']} (\n"
        sql += ",\n".join(columns)
        if len(foreign) > 0:
            sql += ",\n"
            sql += ",\n".join(foreign)
        sql += "\n);"
        print(sql)
        db_cursor.execute(sql)
        uri_col = self.uri_col(prefix)
        sql = f"CREATE UNIQUE INDEX index_{schema['table']}_{uri_col} ON {schema['table']}(\"{uri_col}\")"
        print(sql)
        db_cursor.execute(sql)


    def create_db_tables(self, db_cursor):
        for prefix in self._prefixes:
            self.create_db_table(db_cursor, prefix)


    def import_db_table(self, db_cursor, prefix):
        pass


    def import_db_tables(self, db_cursor):
        for prefix in self._prefixes:
            self.import_db_table(db_cursor, prefix)


# =============================================================================
# Main code follows:

if len(sys.argv) < 3:
    print(f"Usage: {sys.argv[0]} [dt_json_files...] <output_file>")
    sys.exit(1)

out_path = sys.argv[-1]

# Load data files:
dt = DTData()
for infile in sys.argv[1:-1]:
    dt.load(infile)

db_connection = sqlite3.connect(out_path)

dt.create_db_tables(db_connection)
dt.import_db_tables(db_connection)

db_connection.execute('VACUUM;')

# vim: set ts=4 sw=4 tw=0 ai:
