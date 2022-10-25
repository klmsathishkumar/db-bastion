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
with open('connection.json') as f:
    data = json.load(f)

# User Credentials
username =  data["USERNAME"]
password = pass_generator() # Generate it randomly with upper, lower, number characters

# # For reference
# print("Username:",username)
# print("Password:",password)

# Step 1 - Add the security group of Bastion host EC2 instance in inbound rules of the database security group
ec2 = boto3.client('ec2')
sg_list = []

# Params
bastion_sg = "sg-080ded0c2ce0f9093" # Change to Prod DB SG ID
rds_sg = data["RDS_SG"] # Dynamic Field - Change it to the SG of the RDS instance

# Check already present rules in the rds security group
response = ec2.describe_security_groups(GroupIds=[rds_sg])

for i in range(len(response["SecurityGroups"][0]["IpPermissions"][0]["UserIdGroupPairs"])):
    sg_list.append(response["SecurityGroups"][0]["IpPermissions"][0]["UserIdGroupPairs"][i]["GroupId"])

# If the bastion host SG isn't available, creating one
if bastion_sg not in sg_list:
    port_range_start = 5432
    port_range_end = 5432
    protocol = "tcp"

    # security_group = ec2.SecurityGroup(rds_sg)
    
    description = "prod-db-bastion-sg"

    ec2.authorize_security_group_ingress(
        GroupId = rds_sg,
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
    print("\nStep 1 Completed! SG {0} is added in inbound rules of DB SG {1}".format(bastion_sg, rds_sg))
else:
    print("\nAlready {0} is added in the inbound rules of DB {1} SG".format(bastion_sg,rds_sg))

ENDPOINT = data['ENDPOINT']
PORT = data['PORT']
ADMIN_USERNAME = data['ADMIN_USERNAME']
REGION = data['REGION']
DBNAME = data['DBNAME']
ADMIN_PASSWORD = data['ADMIN_PASSWORD']
ENDPOINT = data["ENDPOINT"]

try:
    print("\nFOR MASTER")
    print("\n/usr/pgsql-12/bin/psql -h {0} -U {1} -d postgres".format(ENDPOINT,ADMIN_USERNAME))
    print("\nPassword: ",ADMIN_PASSWORD)
    print("""\nCREATE ROLE "{0}" WITH LOGIN PASSWORD '{1}' NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION VALID UNTIL 'infinity';""".format(username,password))
    print("""\n\c {0}""".format(DBNAME))
    print("""\nGRANT CONNECT ON DATABASE {0} TO "{1}";""".format("postgres",username))
    print("""\nGRANT CONNECT ON DATABASE {0} TO "{1}";""".format(DBNAME,username))
    print("\n\dn")
    # schema_list = [str(i) for i in input("\n").split(",")]
    schema_list = ["public"]
    for j in schema_list:
        schema = j
        print("""\nGRANT USAGE ON SCHEMA {0} TO "{1}" ;""".format(schema,username))
        print("""\nGRANT SELECT ON ALL TABLES IN SCHEMA {0} TO "{1}";""".format(schema,username))
        print("""\nGRANT SELECT ON ALL SEQUENCES IN SCHEMA {0} TO "{1}";""".format(schema,username))
        print("\n")
    print("\n\n")
    print("FOR USER")
    print("\n/usr/pgsql-12/bin/psql -h {0} -U {1} -d {2}".format(ENDPOINT,username,DBNAME))
    print("\nUser Password - ",password)
    print("\n\dt")


    with open("creds.txt",'a+') as f:
	    f.write("""\n{0},{1},{2},{3}""".format(username,password,ENDPOINT,DBNAME))

    
except Exception as e:
    print("Exception occured:",e)

print("""\nStep 2 completed! - {0} is given access to {1}""".format(username,ENDPOINT))


# Step 3 - Add db-bastion-ssm-access policy with this instance id - i-0192fd90c8c2d8b6e for the user in prod
iam = boto3.client('iam')
users_list = []

# Params
groupname = data['GROUPNAME'] # Create a user group with policy (SSM access for the bastion instance)
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
    print("\nStep 3 Completed. Added {0} to group {1}".format(username,groupname))
else:
    print("\nAlready {0} have the access to group {1}".format(username,groupname))


print("\nGreat!! Now the user can acces the DB via SSM. Here are the user credentials \nUsername - {0}\nPassword - {1}".format(username,password))