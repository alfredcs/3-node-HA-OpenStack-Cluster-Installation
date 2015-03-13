#!/usr/bin/python

import getopt, sys, socket

import pycassa
from pycassa.pool import ConnectionPool
from pycassa.util import OrderedDict

def print_map(level, dict):
  for key in dict.keys():
    value = dict[key]
    if type(value) == type(OrderedDict()):
      print indent(level), key, ": {"
      print_map(level+1, value)
      print indent(level), "}"
    elif key == "sig" or key == "psig" or key == "_csh_":
      # these don't render well even though we do decode
      # unicode to utf8, so converting to hex
      print indent(level), key, ":", quote(to_hex_string(value)), ","
    else:
      print indent(level), key, ":", quote(value), ","
    
def to_hex_string(s):
  chars = []
  for i in range(0, len(s)):
    chars.append(hex(ord(s[i:i+1]))[2:])
  return "".join(chars)

def quote(s):
  if not(s.startswith("\"") and s.endswith("\"")):
    return "".join(["\"", unicode(s).encode("utf8"), "\""])
  else:
    return s

def indent(level):
  return ("." * level * 2)

def usage(message=None):
  print "Usage: %s [-h|-s] [-n|--host <Db_host>] [-p|--port <DB_port>] [-k|--key <key_space>] [-t|--table <table_space>]" % (sys.argv[0])
  print "-h|--help: show this message"
  print "-s|--summary: show only keys"
  print "-n|--host: Cassandra DB hostname ot IP"
  print "-p|--port: Cassandra DB service port"
  print "-k|--key: Target key space name"
  print "-t|--table: target table space name"
  sys.exit(-1)
  
def main():
  default_db_host=socket.gethostname()
  default_db_port="9160"
  default_key_space="ContrailAnalytics"
  default_table_space="FlowRecordTable"

  try:
    (opts, args) = getopt.getopt(sys.argv[1:], "n:p:k:t:sh", \
      ["summary", "help"])
  except getopt.GetoptError:
    usage()

  show_summary = False
  for o, a in opts:
#    (k, v) = opt
    if o in ["-h", "--help"]:
      usage()
    elif o in ["-n", "--host"]:
      default_db_host=a
    elif o in ["-p", "--port"]:
      default_db_port=a
    elif o in ["-k", "--key"]:
      default_key_space=a
    elif o in ["-t", "--table"]:
      default_table_space=a
    elif o in ["-s", "--summary"]:
      show_summary = True

  try:
    level = 1
    pool = ConnectionPool(keyspace=default_key_space, server_list=[default_db_host+":"+default_db_port], timeout=0.5, max_retries=2)
    f = pycassa.ColumnFamily(pool, default_table_space)
    row_count=sum(1 for _ in f.get_range())
    if ( row_count >= 0 ):
      	print "HTTP/1.1 200 OK"
      	print "Content-Type: Content-Type: text/plain"
      	print 
      	print "ColumnFamily: %s in KeySpace:%s has %d rows" % (default_table_space, default_key_space, row_count)
      	print
      	print "Cassandra checked!"
      	sys.exit(0)
    else:
	print "HTTP/1.1 500 Internal Server Error"
    	print "Content-Type: Content-Type: text/plain"
    	print
	print "Unable to query ColumnFamily %s" % (default_table_space)
    	sys.exit(1)
  except Exception as e:
    print "HTTP/1.1 503 Service Unavailable"
    print "Content-Type: Content-Type: text/plain"
    print
    print str(e)
    sys.exit(2)
  #except getopt.GetoptError:

if __name__ == "__main__":
  main()

