import subprocess
import sys
import os
import socket

if sys.platform.lower() == "win32":
    os.system('color')

# for i in list(range(31,37))+list(range(91,97)): print("\033["+str(i)+"m\\033["+str(i)+"m TEXT \\033[0;39m\033[0;39m")

class color:
    black = lambda x: '\033[30m' + str(x)+'\033[0;39m'
    red = lambda x: '\033[31m' + str(x)+'\033[0;39m'
    green = lambda x: '\033[32m' + str(x)+'\033[0;39m'
    yellow = lambda x: '\033[33m' + str(x)+'\033[0;39m'
    blue = lambda x: '\033[34m' + str(x)+'\033[0;39m'
    magenta = lambda x: '\033[35m' + str(x)+'\033[0;39m'
    cyan = lambda x: '\033[36m' + str(x)+'\033[0;39m'
    white = lambda x: '\033[37m' + str(x)+'\033[0;39m'
    lime = lambda x: '\033[92m' + str(x)+'\033[0;39m'
    pink = lambda x: '\033[95m' + str(x)+'\033[0;39m'

def cmd(command):
    result = subprocess.check_output(command)
    return result[:-1].decode('utf-8')

def undo_commit():
    print(color.cyan('Undoing commit: '), end = '')
    result = subprocess.call(['git','reset','HEAD~1','--soft'])
    if int(result)==0:
        print(color.yellow('OK'))
    else:
        print(color.red('FAIL'))

def get_commit_hash():
    return cmd(['git','rev-parse','--verify','HEAD'])

def get_branch_name():
    return cmd(['git','rev-parse','--abbrev-ref','HEAD'])

def extract_branch_name(ref):
    if ref.find('/')<0:
        return ref
    return ref[ref.rfind('/')+1:]

def get_stdin_input():
    for line in sys.stdin:
        if not line.strip():
            continue
        return line.strip().split()

# This function will provide env variables for requested server type
def pg_env(pg_server_type):
    if pg_server_type=='pg_branch':
        return (socket.gethostbyname(os.getenv('PG_BRANCH_HOSTNAME')),
            os.getenv('PG_BRANCH_PORT'),
            os.getenv('PG_BRANCH_PASSWORD'),
            os.getenv('PG_BRANCH_USERNAME'))
    if pg_server_type=='pg_master':
        return (socket.gethostbyname(os.getenv('PG_BRANCH_HOSTNAME')),
            os.getenv('PG_BRANCH_PORT'),
            os.getenv('PG_BRANCH_PASSWORD'),
            os.getenv('PG_BRANCH_USERNAME'))
    if pg_server_type=='pg_staging':
        return (socket.gethostbyname(os.getenv('PG_BRANCH_HOSTNAME')),
            os.getenv('PG_BRANCH_PORT'),
            os.getenv('PG_BRANCH_PASSWORD'),
            os.getenv('PG_BRANCH_USERNAME'))
    if pg_server_type=='pg_dev':
        return (socket.gethostbyname(os.getenv('PG_DEV_HOSTNAME')),
        os.getenv('PG_DEV_PORT'),
        os.getenv('PG_DEV_PASSWORD').replace("\"", "\\\""),
        os.getenv('PG_DEV_USERNAME'))

    raise Exception('unknown_env')

# The function is used for diff generation and diff apply
def pg_sync(pg_from_env, 
                   pg_to_env, 
                   pg_from_db, 
                   pg_to_db, 
                   pg_sql_file,
                   pg_apply=False,
                   pg_create_from_db=False, 
                   pg_create_to_db=False):

        
        pg_from_hostname, pg_from_port, pg_from_password, pg_from_username = pg_env(pg_from_env)
        pg_to_hostname, pg_to_port, pg_to_password, pg_to_username = pg_env(pg_to_env)
  
        print(f'postgresql://{pg_to_username}:{pg_to_password}@{pg_to_hostname}:{pg_to_port}/{pg_to_db}')

        if pg_create_from_db:
            try:
                subprocess.call(['psql',f'postgresql://{pg_from_username}:{pg_from_password}@{pg_from_hostname}:{pg_from_port}/', 
                    '-c', f'CREATE DATABASE {pg_from_db}'],
                    stderr=subprocess.DEVNULL)
            except:
                pass 

        if pg_create_to_db:
            try:
                subprocess.call(['psql',f'postgresql://{pg_to_username}:{pg_to_password}@{pg_to_hostname}:{pg_to_port}/', 
                    '-c', f'CREATE DATABASE {pg_to_db}'])
            except:
                pass  
        
        # I did not remember why is this there (?)
        if not pg_from_db:
            cmd(['touch', pg_sql_file])
            sys.exit(0)

        try:
            cmd(['pgquarrel',
                '--file', pg_sql_file,
                # source db
                '--source-dbname', f'hostaddr={pg_from_hostname} port={pg_from_port} dbname={pg_from_db} user={pg_from_username} password={pg_from_password}',
                # target db
                '--target-dbname', f'hostaddr={pg_to_hostname} port={pg_to_port} dbname={pg_to_db} user={pg_to_username} password={pg_to_password}',
                # common settings
                '--table-partition', 'false',
                '--single-transaction', 'true',
                '--extension', 'true',
                '--function', 'true',
                '--procedure', 'true',
                '--exclude-schema', '^(php_test|ci_test|promo)$',
            ])

            print(color.cyan(cmd(['cat', pg_sql_file])))
            print(color.green(pg_sql_file))

            if pg_apply:
                cmd(['psql',f'postgresql://{pg_to_username}:{pg_to_password}@{pg_to_hostname}:{pg_to_port}/{pg_to_db}', 
                    '--set', 'ON_ERROR_STOP=on',
                    '-f', pg_sql_file])

        except Exception as e:
            print(color.red('Diff file generation failed, aborting...'))
            if os.path.exists(pg_sql_file):
                cmd(['rm', pg_sql_file])
            sys.exit(1)

def pg_apply(pg_to_env, pg_to_db, pg_sql_file, pg_create_to_db=False):
    pg_to_hostname, pg_to_port, pg_to_password, pg_to_username = pg_env(pg_to_env)
    if pg_create_to_db:
        try:
            subprocess.call(['psql',f'postgresql://{pg_to_username}:{pg_to_password}@{pg_to_hostname}:{pg_to_port}/', 
                '-c', f'CREATE DATABASE {pg_to_db}'])
        except:
            pass
    cmd(['psql',f'postgresql://{pg_to_username}:{pg_to_password}@{pg_to_hostname}:{pg_to_port}/{pg_to_db}', 
        '--set', 'ON_ERROR_STOP=on',
        '-f', pg_sql_file])

def diff_file_path(name, exit_if_absent=False):
    commit_hash = get_commit_hash()
    print(color.cyan('Commit hash:'), color.yellow(commit_hash))

    sql_diff_path = os.path.join(cmd(['pwd']), '.git', 'sql')
    if not exit_if_absent and not os.path.exists(sql_diff_path):
        cmd(['mkdir', sql_diff_path])

    path = os.path.join(sql_diff_path, commit_hash+'.'+name+'.sql')

    if exit_if_absent and not os.path.exists(sql_diff_path):
        print(color.red('Diff file not found'))
        sys.exit(1)

    return path