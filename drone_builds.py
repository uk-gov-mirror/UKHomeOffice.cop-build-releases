#!/usr/bin/env python

import argparse
import datetime
import json
import os
import re
import requests
import yaml
from prettytable import PrettyTable
from prettytable import PLAIN_COLUMNS


def getDroneBuildsParser():
    parser = argparse.ArgumentParser(description='Drone builds')

    parser.add_argument('-a', '--action', dest='action', default='report', choices=['deploy', 'release', 'report', 'populate'], help='Options are deploy, release (commit sha and build number output), report (builds per repo, summary or detailed), and populate (For releases to staging/production), defaults to report')
    parser.add_argument('-d', '--deploy-to', dest='deploy_to', choices=['production', 'staging'], help='Environment to deploy to')
    parser.add_argument('-r', '--repo', dest='repo', help='Drone repository name')
    parser.add_argument('-s', '--store', dest='repo_store', choices=['github', 'gitlab'], help='Github / Gitlab repository store')
    parser.add_argument('-t', '--report-type', dest='report_type', default='summary', choices=['detailed', 'summary'], help='Type of report, defaults to summary')
    parser.add_argument('-f', '--report-format', dest='report_format', default='table', choices=['list', 'table'], help='Style of report, defaults to table')

    return parser


def overrideArguments(args):
    loc_action = os.environ.get('ACTION')
    if loc_action is not None:
        args.action = loc_action

    loc_deploy_to = os.environ.get('DEPLOY_TO')
    if loc_deploy_to is not None:
        args.deploy_to = loc_deploy_to

    loc_repo = os.environ.get('REPO')
    if loc_repo is not None:
        args.repo = loc_repo

    loc_repo_store = os.environ.get('REPO_STORE')
    if loc_repo_store is not None:
        args.repo_store = loc_repo_store

    loc_report_type = os.environ.get('REPORT_TYPE')
    if loc_report_type is not None:
        args.report_type = loc_report_type

    loc_report_format = os.environ.get('REPORT_FORMAT')
    if loc_report_format is not None:
        args.report_format = loc_report_format

    return args


def validateFile(src_file):
    try:
        data = yaml.safe_load(open(src_file))
        return True
    except yaml.YAMLError as e:
        print(e)
        return False


def getDroneServerUrl(env_var_name):
    drone_server_url = os.environ.get(env_var_name)
    if drone_server_url is None:
        print('Drone server environment variable ' + env_var_name + ' not set')
        return None

    return drone_server_url


def getDroneUserToken(env_var_name):
    drone_user_token = os.environ.get(env_var_name)
    if drone_user_token is None:
        print('Drone user token environment variable ' + env_var_name + ' not set')
        return None

    return drone_user_token


def getDroneTokenString(drone_user_token):
    return {'Authorization': "Bearer " + drone_user_token}


def print_repos_build_info(repo, build_list, report_format):
    if build_list:
        t = PrettyTable(['Environment', 'Build', 'Date', 'Status', 'Commit'])
        t.align = 'l'
        print_repos_build_info.align = 'l'

        if report_format == 'list':
            t.set_style (PLAIN_COLUMNS)

        for build in build_list:
            json_str = json.loads(build)
            deploy_env = 'DEV' if json_str['deploy_to'] == '' else json_str['deploy_to'].upper()
            commit_str = json_str['commit'] if json_str['link_url'] == '' else json_str['link_url']
            formatted_commit = commit_str.split("/")

            if report_format == 'release':
                repo_name = re.sub('UKHomeOffice/', '', repo)
                formatted_repo = re.sub('cop/', '', repo_name)
                print('|' + formatted_repo + '|' + formatted_commit[len(formatted_commit) - 1] + '|' + str(json_str['number']) + '|')
                #print('drone deploy ' + repo + ' ' + str(json_str['number']) + ' staging')
                #print('drone deploy ' + repo + ' ' + str(json_str['number']) + ' production')
            else:
                t.add_row([deploy_env, json_str['number'], datetime.datetime.fromtimestamp(json_str['started_at']), json_str['status'], commit_str])

        if report_format != 'release':
            print(t)


def print_repo_build_info(build_env, build_list, report_format):
    if build_list:
        t = PrettyTable(['Build', 'Date', 'Status', 'Commit', 'Author'])
        t.align = 'l'
        if report_format == 'list':
            t.set_style (PLAIN_COLUMNS)

        print('**' + build_env.upper() + '**')

        for build in build_list:
            json_str = json.loads(build)
            commit_str = json_str['commit'] if json_str['link_url'] == '' else json_str['link_url']
            t.add_row([json_str['number'], datetime.datetime.fromtimestamp(json_str['started_at']), json_str['status'], commit_str, json_str['author']])

        print(t)


def getRepoList(args, header_str, drone_server_url):
    if args.repo is None:
        drone_repos_url = drone_server_url + '/api/user/repos'
        try:
            repos_response = requests.request("GET", drone_repos_url, headers=header_str)
    
            if repos_response.status_code == 200:
                return repos_response.json()
        except Exception as droneError:
            raise(droneError)
    else:
        repo_list = []
        json_dict_obj = { "full_name": args.repo }
        repo_list.append(json_dict_obj)
        return repo_list


def getBuilds(drone_server_url, header_str, repo_name):
    drone_builds_url = drone_server_url + '/api/repos/' + repo_name + '/builds'
        
    try:
        builds_response = requests.request("GET", drone_builds_url, headers=header_str)

        if builds_response.status_code == 200:
            return builds_response.json()
    except Exception as droneError:
        raise(droneError)


def recurse(data, drone_server_url, header_str, action, deploy_to):
    for entry in data:
        repo = data[entry]

        if not('gitlab' in repo):
            try:
                if (isinstance(repo, dict)):
                    iterator = iter(repo)
                    recurse(repo, drone_server_url, header_str, action, deploy_to)
                else:
                    continue
            except TypeError:
                continue
        else:
            if ("gitlab" in drone_server_url and repo['gitlab'] == True) or (not("gitlab" in drone_server_url) and repo['gitlab'] == False):
                try:
                    build_list = getBuilds(drone_server_url, header_str, repo['drone_repo'])
    
                    for build in build_list:
                        if action == 'populate':
                            if (build['branch'] == 'master' and (build['event'] == 'push' or build['event'] == 'deployment')):
                                repo['tag'] = build['commit'].encode('ascii', 'ignore')
                                break
                        else:
                            if repo['tag'] == build['commit'].encode('ascii', 'ignore'):
                                print('drone deploy ' + repo['drone_repo'] + ' ' + str(build['number']) + ' ' + deploy_to)
                                break
                except Exception as buildError:
                    print(str(buildError))


def buildReport(args, drone_server_url, drone_user_token, header_str):
    repo_list = getRepoList(args, header_str, drone_server_url)
    
    for repo in repo_list:
        dev_builds = []
        secrets_builds = []
        staging_builds = []
        prod_builds = []
                
        build_list = getBuilds(drone_server_url, header_str, repo['full_name'])
        if not build_list:
            print('No builds found for ' + repo['full_name'] + '\n')
            continue

        if (args.action == 'report'):
            print('**' + repo['full_name'].upper() + '**')

        for build in build_list:
            if (build['deploy_to'] == 'production'):
                prod_builds.append(json.dumps(build))
            elif (build['deploy_to'] == 'staging'):
                staging_builds.append(json.dumps(build))
            elif (build['deploy_to'] == 'secrets'):
                secrets_builds.append(json.dumps(build))
            else:
                if (build['branch'] == 'master' and (build['event'] == 'push' or build['event'] == 'deployment')):
                    dev_builds.append(json.dumps(build))

        if (args.report_type == 'detailed') and (args.action != 'release'):
            print_repo_build_info('dev', dev_builds, args.report_format)
            print_repo_build_info('secrets', secrets_builds, args.report_format)
            print_repo_build_info('staging', staging_builds, args.report_format)
            print_repo_build_info('production', prod_builds, args.report_format)
        elif (args.report_type == 'summary') or (args.action == 'release'):
            repo_builds = []
            if dev_builds:
                repo_builds.append(dev_builds[0])

            if args.action == 'release':
                print_repos_build_info(repo['full_name'], repo_builds, 'release')
            else:
                if secrets_builds:
                    repo_builds.append(secrets_builds[0])

                if staging_builds:
                    repo_builds.append(staging_builds[0])

                if prod_builds:
                    repo_builds.append(prod_builds[0])

                print_repos_build_info(repo['full_name'], repo_builds, args.report_format)

        if args.action != 'release':
            print('\n')


def process_local(data, yaml_file, drone_server_url, header_str, action, deploy_to):
    if data is None:
        # Validate yaml file
        if not validateFile(yaml_file):
            print('Yaml file is not valid')
            exit(1)
    
        with open(yaml_file, 'r') as stream:
            var_data = yaml.safe_load(stream)
    else:
        var_data = data

    repo_list = []
    recurse(var_data, drone_server_url, header_str, action, deploy_to)
    return var_data


def runAction(args, data, env_server_name, env_token_name):
    drone_server_url = getDroneServerUrl(env_server_name)
    drone_user_token = getDroneUserToken(env_token_name)

    if drone_server_url is None or drone_user_token is None:
        return
        
    header_str = getDroneTokenString(drone_user_token)
    local_filename = 'local.yml'

    if (args.action == 'report') or (args.action == 'release'):
        buildReport(args, drone_server_url, drone_user_token, header_str)
    elif args.action == 'populate' or args.action == 'deploy':
        return process_local(data, local_filename, drone_server_url, header_str, args.action, args.deploy_to)


if __name__ == "__main__":
    parser = getDroneBuildsParser()
    args = overrideArguments(parser.parse_args())

    data = None
    process_gitlab = True
    process_github = True

    if args.repo is not None or args.repo_store is not None:
        if args.repo_store is None:
            print('If you specify a repo, please specify a store')
            exit(1)
        else:
            if args.repo_store == 'gitlab':
                process_github = False
            else:
                process_gitlab = False

    if args.action == 'deploy':
        if args.deploy_to is None:
            print('If you specify a deployment, please specify an environment to deploy to')
            exit(1)

    print('Running with the following options:')
    print('-----------------------------------')
    print('Action: ' + args.action)
 
    print('Deploy to: ' + str(args.deploy_to) + ' (applicable for deploy action)')
    print('Repo: ' + str(args.repo) + ' (only applicable for report action)')
    print('Repo store: ' + str(args.repo_store) + ' (applicable when repo is is provided, or to limit processing to a particular store)')
    print('Report format: ' + args.report_format + ' (applicable for report action)')
    print('Report type: ' + args.report_type + ' (applicable for report action)\n')

    if process_github:
        data = runAction(args, data, 'GITHUB_DRONE_SERVER', 'GITHUB_DRONE_TOKEN')

    if process_gitlab:
        data = runAction(args, data, 'GITLAB_DRONE_SERVER', 'GITLAB_DRONE_TOKEN')

    if (data is not None) and (args.action == 'populate'):
        print(yaml.dump(data))
