#! /usr/bin/env python3
#=========================================================================
# mflowgen
#=========================================================================
#
#  -h --help     Display this message
#  -v --version  Version info
#     --design   Name of the design
#     --backend  Backend build system: make, ninja
#
# Stash-related options:
#
#  -d --dir      string --  Path for stash init, stash link
#  -s --step     int    --  Step number for stash push
#  -m --msg      string --  Push message for stash push
#     --hash     string --  Hash for stash drop
#

#
# Author : Christopher Torng
# Date   : June 2, 2019
#

import argparse
import importlib
import os
import sys
import yaml

from mflowgen import BuildOrchestrator, StashHandler
from mflowgen import MakeBackend, NinjaBackend

#-------------------------------------------------------------------------
# Command line processing
#-------------------------------------------------------------------------

class ArgumentParserWithCustomError(argparse.ArgumentParser):
  def error( self, msg = "" ):
    if ( msg ): print("\n ERROR: %s" % msg)
    print("")
    file = open( sys.argv[0] )
    for ( lineno, line ) in enumerate( file ):
      if ( line[0] != '#' ): sys.exit(msg != "")
      if ( (lineno == 2) or (lineno >= 4) ): print( line[1:].rstrip("\n") )

def parse_cmdline():
  p = ArgumentParserWithCustomError( add_help=False )
  p.add_argument( "-v", "--version", action="store_true"          )
  p.add_argument( "-h", "--help",    action="store_true"          )
  p.add_argument(       "--design",  default="../designs/GcdUnit" )
  p.add_argument(       "--backend", default="make",
                                     choices=("make", "ninja")    )
  # Stash-related arguments
  p.add_argument(       "args", type=str, nargs='*' ) # positional
  p.add_argument( "-d", "--dir"                                   )
  p.add_argument( "-s", "--step", type=int                        )
  p.add_argument( "-m", "--msg"                                   )
  p.add_argument(       "--hash"                                  )
  opts = p.parse_args()
  if opts.help and not opts.args: p.error() # print help only if not stash
  return opts

#-------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------

def main():

  opts = parse_cmdline()

  # Version

  if opts.version:
    print( 'mflowgen 0.1.0' )
    return

  # Dispatch to StashHandler if positional arguments for stash are given

  if opts.args and opts.args[0] == 'stash':
    shandler = StashHandler()
    shandler.launch(
      args  = opts.args[1:],
      help_ = opts.help,
      dir_  = opts.dir,
      step  = opts.step,
      msg   = opts.msg,
      hash_ = opts.hash,
    )
    return

  # Check that this design directory exists

  if not os.path.exists( opts.design ):
    raise ValueError(
      'Directory not found at path "{}"'.format( opts.design ) )

  # Read the .mflowgen.yml metadata in the design directory

  yaml_path = opts.design + '/.mflowgen.yml'
  yaml_path = os.path.abspath( yaml_path )

  with open( yaml_path ) as fd:
    try:
      data = yaml.load( fd, Loader=yaml.FullLoader )
    except AttributeError:
      # PyYAML for python2 does not have FullLoader
      data = yaml.load( fd )

  # Locate the construct script

  try:
    construct_path = data['construct']
  except KeyError:
    raise KeyError(
      'YAML file "{}" must have key named construct'.format( yaml_path ) )

  if not construct_path.startswith( '/' ):
    construct_path = opts.design + '/' + construct_path

  construct_path = os.path.abspath( construct_path )

  if not os.path.exists( construct_path ):
    raise ValueError(
      'Construct script not found at path "{}"'.format( construct_path ) )

  # Import the graph for this design

  c_dirname  = os.path.dirname( construct_path )
  c_basename = os.path.splitext( os.path.basename( construct_path ) )[0]

  sys.path.append( c_dirname )

  try:
    construct = importlib.import_module( c_basename )
  except ImportError:
    raise ImportError( 'No module named construct in "{}"'.format(
                         construct_path ) )

  # Construct the graph

  g = construct.construct()

  # Generate the build files (e.g., Makefile) for the selected backend
  # build system

  if opts.backend == 'make':
    backend_cls = MakeBackend
  elif opts.backend == 'ninja':
    backend_cls = NinjaBackend

  b = BuildOrchestrator( g, backend_cls )
  b.build()

  # Done

  list_target   = opts.backend + " list"
  status_target = opts.backend + " status"

  print( "Targets: run \"" + list_target   + "\" and \""
                           + status_target + "\"" )
  print()


main()



