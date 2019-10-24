# cop-build-releases

This is being developed by the UK Home Office and is used to store the scripts required to interact with Drone to display build information, populate a deployment file and initiate deployments for COP builds. A docker image is created which is utilised in the Gitlab `manifest` repository.

# Requirements

* Drone credentials
* Python3, virtualenv

# Usage

This can be used from your laptop and has been integrated into the pipeline steps for the COP Gitlab manifest repository.

# Drone Secrets

Name|Example value
---|---
dev_drone_aws_access_key_id|https://console.aws.amazon.com/iam/home?region=eu-west-2#/users/bf-it-devtest-drone?section=security_credentials
dev_drone_aws_secret_access_key|https://console.aws.amazon.com/iam/home?region=eu-west-2#/users/bf-it-devtest-drone?section=security_credentials
drone_public_token|Drone token (Global for all github repositories and environments)
quay_password|xxx (Global for all repositories and environments)
quay_username|docker (Global for all repositories and environments)
slack_webhook|https://hooks.slack.com/services/xxx/yyy/zzz (Global for all repositories and environments)

# Python script

## Tools

Install virtual environment

```
pip install virtualenv
```

Create a virtual environment
```
virtualenv build_venv
source build_venv/bin/activate
pip install -r requirements.txt
```

##  Options

### Usage

```
drone_builds.py [-h] [-a {deploy,report,populate}]
                       [-d {production,staging}] [-r REPO]
                       [-s {github,gitlab}] [-t {detailed,summary}]
                       [-f {list,table}]

optional arguments:
  -h, --help            show this help message and exit
  -a {deploy,report,populate}, --action {deploy,report,populate}
                        Options are report (builds per repo, summary or
                        detailed), populate (For releases to
                        staging/production), and deploy, defaults to report
  -d {production,staging}, --deploy-to {production,staging}
                        Environment to deploy to
  -r REPO, --repo REPO  Drone repository name
  -s {github,gitlab}, --store {github,gitlab}
                        Github / Gitlab repository store
  -t {detailed,summary}, --report-type {detailed,summary}
                        Type of report, defaults to summary
  -f {list,table}, --report-format {list,table}
                        Style of report, defaults to table
```

#### Environment variable overrides

- ACTION
- DEPLOY_TO
- REPO
- REPO_STORE
- REPORT_FORMAT
- REPORT_TYPE

### Summary report

The following report will be displayed in a table or list format for all repositories, or a specific repository, depending on the options supplied. Prints the last build for each environment.

#### Command line

```
./drone_builds.py -a report -t summary
./drone_builds.py -a report -r UKHomeOffice/RefData -s github -t summary -f list
```

#### Drone deployment

```
drone deploy cop/manifest 5 dev
drone deploy -p REPO=UKHomeOffice/RefData -p REPO_STORE=github -p REPORT_FORMAT=list cop/manifest 5 dev
```

UKHOMEOFFICE/REFDATA

Environment|Build|Date|Status|Commit
---|---|---|---|---
DEV|773|2019-10-21 15:06:09|success|https://github.com/UKHomeOffice/RefData/commit/84f21660746c1cef1b3348d85fd2a8ba3449a04b
SECRETS|746|2019-10-16 15:21:04|success|https://github.com/UKHomeOffice/RefData/commit/fb273d5c0134d32be3fadbda89948b8e05836d8e
STAGING|748|2019-10-16 15:35:04|success|https://github.com/UKHomeOffice/RefData/commit/fb273d5c0134d32be3fadbda89948b8e05836d8e
PRODUCTION|749|2019-10-16 16:53:43|success|https://github.com/UKHomeOffice/RefData/commit/fb273d5c0134d32be3fadbda89948b8e05836d8e

### Detailed report

The following report will be displayed in a table or list format for all repositories, or a specific repository, depending on the options supplied. Prints all the builds for each environment.

#### Command line

```
./drone_builds.py -a report -t detailed
./drone_builds.py -a report -r UKHomeOffice/RefData -s github -t detailed -f list
```

#### Drone deployment

```
drone deploy -p REPORT_TYPE=detailed cop/manifest 5 dev
drone deploy -p REPO=UKHomeOffice/RefData -p REPO_STORE=github -p REPORT_TYPE=detailed -p REPORT_FORMAT=list cop/manifest 5 dev
```

UKHOMEOFFICE/REFDATA

DEV

Build|Date|Status|Commit|Author
---|---|---|---|---
773|2019-10-21 15:06:09|success|https://github.com/UKHomeOffice/RefData/commit/84f21660746c1cef1b3348d85fd2a8ba3449a04b|xxx
725|2019-10-07 16:18:18|success|https://github.com/UKHomeOffice/RefData/commit/32789272987305ec4fe535dc5c607cbc17584461|xxx

SECRETS

Build|Date|Status|Commit|Author
---|---|---|---|---
746|2019-10-16 15:21:04|success|https://github.com/UKHomeOffice/RefData/commit/fb273d5c0134d32be3fadbda89948b8e05836d8e|xxx
738|2019-10-16 10:56:21|success|https://github.com/UKHomeOffice/RefData/commit/dbd0d48e60f09f02fb7337ebc3c1096ccdcb4b2b|xxx

STAGING

Build|Date|Status|Commit|Author
---|---|---|---|---
748|2019-10-16 15:35:04|success|https://github.com/UKHomeOffice/RefData/commit/fb273d5c0134d32be3fadbda89948b8e05836d8e|xxx
727|2019-10-08 13:52:03|success|https://github.com/UKHomeOffice/RefData/commit/32789272987305ec4fe535dc5c607cbc17584461|xxx

PRODUCTION

Build|Date|Status|Commit|Author
---|---|---|---|---
749|2019-10-16 16:53:43|success|https://github.com/UKHomeOffice/RefData/commit/fb273d5c0134d32be3fadbda89948b8e05836d8e|xxx
728|2019-10-08 14:03:10|success|https://github.com/UKHomeOffice/RefData/commit/32789272987305ec4fe535dc5c607cbc17584461|xxx

### Populate yaml

This step is run from the Gitlab `manifest` repository `.drone.yml`.

When we release to staging the local.yml file needs to be updated so that local dev builds are correct according to what is in production. This was a manual task and has been automated here. In order to determine which repository store, drone CI server and repository is used for each microservice, 2 new attributes have been added to the microservices' config: `gitlab` and `drone_repo`. The script traverses the yaml file twice, first with github drone server url and token, and then gitlab and its respective values, querying drone for the repository's builds and updating the tag to the latest master commit id. The updated yaml is then printed out and currently needs to be checked in manually.

#### Command line

Copy the manifest repository local.yml to the python script directory

```
cp <path-to-manifest-repo>/local.yml .
./drone_builds.py -a populate > local.yml.new
./drone_builds.py -a populate -s github > local.yml.new
```

Copy the local.yml.new file back to the manifest repo local.yml and commit if you plan to release these changes to staging.

#### Drone deployment

```
drone deploy -p ACTION=populate -p REPO_STORE=github cop/manifest 5 dev
```

### Deploy

This step is run from the Gitlab `manifest` repository `.drone.yml`.

This is currently only printing out drone command line commands, it does not actually deploy any builds.

The script traverses the yaml file twice, printing out the drone commands for deploying to staging or production using the `tag` value found for each microservice. Execute the drone commands to deploy staging and production.

#### Command line

Copy the manifest repository local.yml to the python script directory.

```
cp <path-to-manifest-repo>/local.yml .
./drone_builds.py -a deploy -d staging
```

#### Drone deployment

```
drone deploy -p ACTION=deploy -p DEPLOY_TO=staging cop/manifest 5 dev
```

## Finish

Deactivate the virtualenv
```
deactivate
```
