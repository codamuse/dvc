from __future__ import print_function

import os
import sys
import argparse
from multiprocessing import cpu_count

from dvc.command.find import CmdFind
from dvc.command.fsck import CmdFsck
from dvc.command.init import CmdInit
from dvc.command.remove import CmdRemove
from dvc.command.run import CmdRun
from dvc.command.repro import CmdRepro
from dvc.command.data_sync import CmdDataPush, CmdDataPull, CmdDataStatus
from dvc.command.lock import CmdLock
from dvc.command.gc import CmdGC
from dvc.command.add import CmdAdd
from dvc.command.show_workflow import CmdShowWorkflow
from dvc.command.instance_create import CmdInstanceCreate
from dvc.command.config import CmdConfig
from dvc.command.show_pipeline import CmdShowPipeline
from dvc.command.checkout import CmdCheckout
from dvc.stage import Stage
from dvc import VERSION


def parse_args(argv=None):
    # Common args
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
                        '-q',
                        '--quiet',
                        action='store_true',
                        default=False,
                        help='Be quiet.')
    parent_parser.add_argument(
                        '-v',
                        '--verbose',
                        action='store_true',
                        default=False,
                        help='Be verbose.')

    parent_parser.add_argument(
                        '-b',
                        '--branch',
                        metavar='BRANCH',
                        help='Execute a command in the branch.')
    parent_parser.add_argument(
                        '-n',
                        '--new-branch',
                        metavar='BRANCH',
                        help='Create a new branch and execute a command in the branch.')

    # Main parser
    desc = 'Data Version Control'
    parser = argparse.ArgumentParser(
                        prog='dvc',
                        description=desc,
                        parents=[parent_parser],
                        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('-V',
                        '--version',
                        action='version',
                        version='%(prog)s ' + VERSION)

    # Sub commands
    subparsers = parser.add_subparsers(
                        dest='cmd',
                        help='Use dvc CMD --help for command-specific help')

    # NOTE: Workaround for bug in Python 3
    if sys.version_info[0] == 3:
        subparsers.required = True
        subparsers.dest = 'cmd'

    # Init
    init_parser = subparsers.add_parser(
                        'init',
                        parents=[parent_parser],
                        help='Initialize dvc over a directory (should already be a git dir).')
    init_parser.set_defaults(func=CmdInit)

    # Run
    run_parser = subparsers.add_parser(
                        'run',
                        parents=[parent_parser],
                        help='Run command')
    run_parser.add_argument('-d',
                        '--deps',
                        action='append',
                        default=[],
                        help='Declare dependencies for reproducible cmd.')
    run_parser.add_argument('-o',
                        '--outs',
                        action='append',
                        default=[],
                        help='Declare output data file (sync to cloud) for reproducible cmd.')
    run_parser.add_argument('-O',
                        '--outs-no-cache',
                        action='append',
                        default=[],
                        help='Declare output regular file (sync to Git) for reproducible cmd.')
    run_parser.add_argument('-l',
                        '--lock',
                        action='store_true',
                        default=False,
                        help='Lock data item - disable reproduction.')
    run_parser.add_argument('-f',
                        '--file',
                        help='Specify name of the state file')
    run_parser.add_argument('-c',
                        '--cwd',
                        default=os.path.curdir,
                        help='Directory to run your command and place state file in')
    run_parser.add_argument(
                        '--no-exec',
                        action='store_true',
                        default=False,
                        help="Only create stage file without actually running it")
    run_parser.add_argument(
                        'command',
                        nargs=argparse.REMAINDER,
                        help='Command or command file to execute')
    run_parser.set_defaults(func=CmdRun)

    # Parent parser used in sync/pull/push
    parent_sync_parser = argparse.ArgumentParser(
                        add_help=False,
                        parents=[parent_parser])
    parent_sync_parser.add_argument('-j',
                        '--jobs',
                        type=int,
                        default=cpu_count(),
                        help='Number of jobs to run simultaneously.')

    # Pull
    pull_parser = subparsers.add_parser(
                        'pull',
                        parents=[parent_sync_parser],
                        help='Pull data files from the cloud')
    pull_parser.set_defaults(func=CmdDataPull)

    # Push
    push_parser = subparsers.add_parser(
                        'push',
                        parents=[parent_sync_parser],
                        help='Push data files to the cloud')
    push_parser.set_defaults(func=CmdDataPush)

    # Status
    status_parser = subparsers.add_parser(
                        'status',
                        parents=[parent_sync_parser],
                        help='Show status for data files')
    status_parser.set_defaults(func=CmdDataStatus)

    # Repro
    repro_parser = subparsers.add_parser(
                        'repro',
                        parents=[parent_parser],
                        help='Reproduce data')
    repro_parser.add_argument(
                        'targets',
                        nargs='*',
                        default=[Stage.STAGE_FILE],
                        help='Data items or stages to reproduce.')
    repro_parser.add_argument('-f',
                        '--force',
                        action='store_true',
                        default=False,
                        help='Reproduce even if dependencies were not changed.')
    repro_parser.add_argument('-s',
                        '--single-item',
                        action='store_true',
                        default=False,
                        help='Reproduce only single data item without recursive dependencies check.')
    repro_parser.set_defaults(func=CmdRepro)

    # Remove
    remove_parser = subparsers.add_parser(
                        'remove',
                        parents=[parent_parser],
                        help='Remove data item from data directory.')
    remove_parser.add_argument('targets',
                        nargs='+',
                        help='Target to remove - file or directory.')
    remove_parser.set_defaults(func=CmdRemove)

    # Add
    import_parser = subparsers.add_parser(
                        'add',
                        parents=[parent_parser],
                        help='Add files/directories to dvc')
    import_parser.add_argument(
                        'targets',
                        nargs='+',
                        help='Input files/directories')
    import_parser.set_defaults(func=CmdAdd)

    # Lock
    lock_parser = subparsers.add_parser(
                        'lock',
                        parents=[parent_parser],
                        help='Lock')
    lock_parser.add_argument('-u',
                        '--unlock',
                        action='store_true',
                        default=False,
                        help='Unlock stage - enable reproduction.')
    lock_parser.add_argument(
                        'files',
                        nargs='*',
                        default=[Stage.STAGE_FILE],
                        help='Stages to lock or unlock.')
    lock_parser.set_defaults(func=CmdLock)

    # Garbage collector
    gc_parser = subparsers.add_parser(
                        'gc',
                        parents=[parent_parser],
                        help='Collect garbage')
    gc_parser.set_defaults(func=CmdGC)

    # Cloud
    ex_parser = subparsers.add_parser(
                        'ex',
                        parents=[parent_parser],
                        help='Experimental commands')
    ex_subparsers = ex_parser.add_subparsers(
                        dest='cmd',
                        help='Use dvc cloud CMD --help for command-specific help')

    cloud_parser = ex_subparsers.add_parser(
                        'cloud',
                        parents=[parent_parser],
                        help='Cloud manipulation')
    cloud_subparsers = cloud_parser.add_subparsers(
                        dest='cmd',
                        help='Use dvc cloud CMD --help for command-specific help')

    # Instance create
    instance_create_parser = cloud_subparsers.add_parser(
                        'create',
                        help='Create cloud instance')
    instance_create_parser.add_argument('name',
                                        # metavar='',
                                        nargs='?',
                                        help='Instance name.')
    instance_create_parser.add_argument('-c',
                                        '--cloud',
                                        # metavar='',
                                        help='Cloud: AWS, GCP.')
    instance_create_parser.add_argument('-t',
                                        '--type',
                                        # metavar='',
                                        help='Instance type.')
    instance_create_parser.add_argument('-i',
                                        '--image',
                                        # metavar='',
                                        help='Instance image.')
    instance_create_parser.add_argument('--spot-price',
                                        metavar='PRICE',
                                        help='Spot instance price in $ i.e. 1.54')
    instance_create_parser.add_argument('--spot-timeout',
                                        metavar='TIMEOUT',
                                        type=int,
                                        help='Spot instances waiting timeout in seconds.')
    instance_create_parser.add_argument('--keypair-name',
                                        metavar='KEYPAIR',
                                        help='The name of key pair for instance launch')
    instance_create_parser.add_argument('--keypair-dir',
                                        metavar='DIR',
                                        help='The directory of key pairs')
    instance_create_parser.add_argument('--security-group',
                                        metavar='GROUP',
                                        help='Security group')
    instance_create_parser.add_argument('--region',
                                        help='Region')
    instance_create_parser.add_argument('--zone',
                                        help='Zone')
    instance_create_parser.add_argument('--subnet-id',
                                        metavar='SUBNET',
                                        help='Subnet ID')
    instance_create_parser.add_argument('--storage',
                                        # metavar='',
                                        help='The name of attachable storage volume.')
    # WHERE EBS IS?
    instance_create_parser.add_argument('--monitoring',
                                        action='store_true',
                                        default=False,
                                        help='Enable EC2 instance monitoring')
    instance_create_parser.add_argument('--ebs-optimized',
                                        action='store_true',
                                        default=False,
                                        help='Enable EBS I\O optimization')
    instance_create_parser.add_argument('--disks-to-ride0',
                                        action='store_true',
                                        default=False,
                                        help='Detect all ephemeral disks and stripe together in raid-0')
    instance_create_parser.set_defaults(func=CmdInstanceCreate)

    # Config
    config_parser = subparsers.add_parser(
                        'config',
                        parents=[parent_parser],
                        help='Get or set repository options')
    config_parser.add_argument('-u',
                        '--unset',
                        default=False,
                        action='store_true',
                        help='Unset option')
    config_parser.add_argument('name',
                        help='Option name')
    config_parser.add_argument('value',
                        nargs='?',
                        default=None,
                        help='Option value')
    config_parser.set_defaults(func=CmdConfig)

    # Show
    show_parser = subparsers.add_parser(
                        'show',
                        parents=[parent_parser],
                        help='Show graphs')
    show_subparsers = show_parser.add_subparsers(
                        dest='cmd',
                        help='Use `dvc show CMD` --help for command-specific help')

    pipeline_parser = show_subparsers.add_parser(
                        'pipeline',
                        parents=[parent_parser],
                        help='Show pipeline image')
    pipeline_parser.add_argument(
                        'target',
                        nargs='*',
                        help='Target data directory')
    pipeline_parser.set_defaults(func=CmdShowPipeline)

    workflow_parser = show_subparsers.add_parser(
                        'workflow',
                        parents=[parent_parser],
                        help='Show workflow image. It collapses DVC repro commits if possible.')
    workflow_parser.add_argument(
                        'target',
                        nargs='?',
                        help='Target metric data file')
    workflow_parser.add_argument(
                        '-d',
                        '--dvc-commits',
                        action='store_true',
                        default=False,
                        help='Show DVC repro commits.')
    workflow_parser.add_argument(
                        '-a',
                        '--all-commits',
                        action='store_true',
                        default=False,
                        help='Show all commits')
    workflow_parser.add_argument(
                        '-m',
                        '--max-commits',
                        metavar='M',
                        type=int,
                        default=4,
                        help='Max commits per graph vertex. 4 by default.')

    workflow_parser.set_defaults(func=CmdShowWorkflow)

    # Checkout
    checkout_parser = subparsers.add_parser(
                        'checkout',
                        parents=[parent_parser],
                        help='Checkout')
    checkout_parser.set_defaults(func=CmdCheckout)

    # Find
    find_parser = subparsers.add_parser(
                        'find',
                        parents=[parent_parser],
                        help='Find branch name')
    find_parser.set_defaults(func=CmdFind)
    find_parser.add_argument(
                        'branch_name',
                        nargs='?',
                        help='Branch name regexp.')
    find_parser.add_argument(
                        'target',
                        nargs='?',
                        help='Target metric file.')
    find_parser.add_argument(
                        '-c',
                        '--criteria',
                        help='Search criteria. By default it finds max.',
                        choices=['max', 'min', 'all'],
                        default='max')
    find_parser.add_argument(
                        '-s',
                        '--show-value',
                        action='store_true',
                        default=False,
                        help='Show metrics value.')

    fsck_parser = subparsers.add_parser(
                        'fsck',
                        parents=[parent_parser],
                        help='Data file consistency check')
    fsck_parser.add_argument(
                        'targets',
                        nargs='*',
                        help='Data files to check')
    fsck_parser.add_argument(
                        '-p',
                        '--physical',
                        action='store_true',
                        default=False,
                        help='Compute actual md5')
    fsck_parser.add_argument(
                        '-a',
                        '--all',
                        action='store_true',
                        default=False,
                        help='Show all tracked files including correct ones')
    fsck_parser.set_defaults(func=CmdFsck)

    return parser.parse_args(argv)
