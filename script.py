# Things to be done for giving a DB Bastion Access to a user for a new database
# Add the security group of Bastion host EC2 instance in inbound rules of the database security group
# Create a user in the required database
# Add db-bastion-ssm-access policy with this instance id - i-0192fd90c8c2d8b6e for the user in prod

import boto3
import psycopg2
import json
import pprint
import string
import random

# Random password generator
def pass_generator(size=12, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
    return ''.join(random.choice(chars) for _ in range(size))

# User Credentials
username = "***********.s@fourkites.com" # Dynamic field - Set it to the user email to be given access
password = pass_generator() # Generate it randomly with upper, lower, number characters

# Step 1 - Add the security group of Bastion host EC2 instance in inbound rules of the database security group
ec2 = boto3.client('ec2')
sg_list = []

# Params
bastion_sg = "sg-041b9bda37b6482aa" # Change to Prod DB SG ID
rds_sg = "sg-09beea780597183ce" # Dynamic Field - Change it to the SG of the RDS instance

# Check already present rules in the rds security group
response = ec2.describe_security_groups(GroupIds=[rds_sg])

for i in range(len(response["SecurityGroups"][0]["IpPermissions"][0]["UserIdGroupPairs"])):
    sg_list.append(response["SecurityGroups"][0]["IpPermissions"][0]["UserIdGroupPairs"][i]["GroupId"])

# If the bastion host SG isn't available, creating one
if bastion_sg not in sg_list:
    port_range_start = 5432
    port_range_end = 5432
    protocol = "tcp"

    security_group = ec2.SecurityGroup(rds_sg)
    
    description = "prod-db-bastion-sg"

    security_group.authorize_ingress(
        DryRun=False,
        IpPermissions=[
            {
                'FromPort': port_range_start,
                'ToPort': port_range_end,
                'IpProtocol': protocol,
                'UserIdGroupPairs': [
                    {
                        'GroupId': bastion_sg,
                        'Description':description
                    },
                ],
            }
        ]
    )
    print("Step 1 Completed! SG {0} is added in inbound rules of DB SG {1}".format(bastion_sg, rds_sg))
else:
    print("Already {0} is added in the inbound rules of DB {1} SG".format(bastion_sg,rds_sg))

# Step 2 - Create a user in the required database
# CREATE ROLE "ayrdrie.palmer@fourkites.com" WITH LOGIN PASSWORD 'DBjR045Y30yO' NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION VALID UNTIL 'infinity';
# GRANT CONNECT ON DATABASE facilities TO "ayrdrie.palmer@fourkites.com";
# GRANT USAGE ON SCHEMA public TO "ayrdrie.palmer@fourkites.com" ;
# GRANT SELECT ON ALL TABLES IN SCHEMA public TO "ayrdrie.palmer@fourkites.com";
# GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO "ayrdrie.palmer@fourkites.com";

with open('connection.json') as f:
    data = json.load(f)

ENDPOINT = data['ENDPOINT']
PORT = data['PORT']
USER = data['USER']
REGION = data['REGION']
# DBNAME = data['DBNAME']
TOKEN = data['TOKEN']

schema = "public"

#gets the credentials from .aws/credentials
session = boto3.Session()
client = session.client('rds')

try:
    conn = psycopg2.connect(host=ENDPOINT, port=PORT, database="postgres", user=USER, password=TOKEN, sslrootcert="SSLCERTIFICATE")
    cur = conn.cursor()

    res = cur.execute("""CREATE ROLE "{0}" WITH LOGIN PASSWORD '{1}' NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION VALID UNTIL 'infinity';""".format(username,password))
    print("Create Role Command", res)

    res = cur.execute("""SELECT datname FROM pg_database WHERE datistemplate = false;""")
    print("List of Databases:")
    pprint(res)
    db_list = input("Enter the database(s) number(s)\nIf more than one enter with comma\nExample: 1,2,3\n")
    db_list = [int(i) for i in input().split(",")]

    for DBNAME in db_list:
        res = cur.execute("""GRANT CONNECT ON DATABASE {0} TO "{1}";""".format(DBNAME,username))
        print("Grant access for the database Command",res)

        res = cur.execute("""SELECT schema_name FROM information_schema.schemata;""")
        print("List of schemas:")
        pprint(res)
        schema_list = input("Enter the schema(s) number(s)\nIf more than one enter with comma\nExample: 1,2,3\n")
        schema_list = [int(i) for i in input().split(",")]

        for schema in schema_list:
            res = cur.execute("""GRANT USAGE ON SCHEMA {0} TO "{1}" ;""".format(schema,username))
            print("Grant usage on schema: {0}".format(schema),res)
            res = cur.execute("""GRANT SELECT ON ALL TABLES IN SCHEMA {0} TO "{1}";""".format(schema,username))
            print("Grant select on all tables:",res)
            res = cur.execute("""GRANT SELECT ON ALL SEQUENCES IN SCHEMA {0} TO "{1}";""".format(schema,username))
            print("Grant select on all sequences",res)

except Exception as e:
    print("Exception occured:",e)


# Step 3 - Add db-bastion-ssm-access policy with this instance id - i-0192fd90c8c2d8b6e for the user in prod
iam = boto3.client('iam')
users_list = []

# Params
groupname = 'test1' # Create a user group with policy (SSM access for the bastion instance)
response = iam.get_group(GroupName=groupname)

# getting all users in the group to check whether is the user already there in the iam user group
for i in range(len(response["Users"])):
    users_list.append(response["Users"][i]["UserName"])

# if the user not available, adding them
if username not in users_list:
    response = iam.add_user_to_group(
        GroupName = groupname,
        UserName = username
    )
    print("Step 3 Completed. Added {0} to group {1}".format(username,groupname))
else:
    print("Already {0} have the access to group {1}".format(username,groupname))


print("Great!! Now the user can acces the DB via SSM. Here are the user credentials \nUsername - {0}\nPassword - {1}".format(username,password))