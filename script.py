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

# Step 2 - Create a user in the required database
# CREATE ROLE "ayrdrie.palmer@fourkites.com" WITH LOGIN PASSWORD 'DBjR045Y30yO' NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION VALID UNTIL 'infinity';
# GRANT CONNECT ON DATABASE facilities TO "ayrdrie.palmer@fourkites.com";
# GRANT USAGE ON SCHEMA public TO "ayrdrie.palmer@fourkites.com" ;
# GRANT SELECT ON ALL TABLES IN SCHEMA public TO "ayrdrie.palmer@fourkites.com";
# GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO "ayrdrie.palmer@fourkites.com";

ENDPOINT = data['ENDPOINT']
PORT = data['PORT']
ADMIN_USERNAME = data['ADMIN_USERNAME']
REGION = data['REGION']
# DBNAME = data['DBNAME']
ADMIN_PASSWORD = data['ADMIN_PASSWORD']

db_list = []
schema_list = []
admin_list = []
final_db_list = []
#gets the credentials from .aws/credentials
print("test")

try:
    print("inside try")
    conn = psycopg2.connect(host=ENDPOINT, port=PORT, database="postgres", user=ADMIN_USERNAME, password=ADMIN_PASSWORD, sslrootcert="SSLCERTIFICATE")
    cur = conn.cursor()

    res = cur.execute("""CREATE ROLE "{0}" WITH LOGIN PASSWORD '{1}' NOSUPERUSER INHERIT NOCREATEDB NOCREATEROLE NOREPLICATION VALID UNTIL 'infinity';""".format(username,password))
    cur.execute("COMMIT")

    cur.execute("""SELECT datname FROM pg_database WHERE datistemplate = false;""")
    res = cur.fetchall()
    print("\nList of Databases:")
    # pprint(res)
    for r in res:
        db_list.append(r[0])

    for k in range(len(db_list)):
        print(k+1,db_list[k])

    db_list_inp = input("\nEnter the database(s) number(s)\nIf more than one enter with comma\nExample: 1,2,3\n")
    db_list_inp = [int(i) for i in db_list_inp.split(",")]
    # print(db_list_inp)
    
    for i in db_list_inp:

        db_name = db_list[i-1]
        final_db_list.append(db_name)
        print("\nProcessing for Database -",db_name)
        res = cur.execute("""GRANT CONNECT ON DATABASE {0} TO "{1}";""".format(db_name,username))
        print("\nGrant access for the database ",db_name)
        cur.close()
        conn.close()
        conn = psycopg2.connect(host=ENDPOINT, port=PORT, database=db_name, user=ADMIN_USERNAME, password=ADMIN_PASSWORD, sslrootcert="SSLCERTIFICATE")
        cur = conn.cursor()
        cur.execute("""SELECT current_database()""")
        print("\nThe current database is :",cur.fetchall()[0][0])
        cur.execute("""SELECT * FROM information_schema.schemata;""")
        res = cur.fetchall()
        print("\nList of schemas:")
        for s in res:
            schema_list.append(s[1])
            admin_list.append(s[2])
        # print(schema_list)
        # print(admin_list)
        for l in range(len(schema_list)):
            print(l+1,schema_list[l],admin_list[l])

        schema_list_inp = input("\nEnter the schema(s) number(s)\nIf more than one enter with comma\nExample: 1,2,3\n")
        schema_list_inp = [int(i) for i in schema_list_inp.split(",")]
        # print("Sch Inp",schema_list_inp)
        for j in schema_list_inp:
            schema =  schema_list[j-1]
            print("\nProcessing for schema -",schema)
            res = cur.execute("""GRANT USAGE ON SCHEMA {0} TO "{1}" ;""".format(schema,username))
            print("Grant usage on schema: {0}".format(schema))
            res = cur.execute("""GRANT SELECT ON ALL TABLES IN SCHEMA {0} TO "{1}";""".format(schema,username))
            print("Grant select on all tables")
            res = cur.execute("""GRANT SELECT ON ALL SEQUENCES IN SCHEMA {0} TO "{1}";""".format(schema,username))
            print("\nGrant select on all sequences")
            print("\nAccess given for Schema -",schema)
            cur.execute("COMMIT")
        print("\nAccess given for database -",db_name)
    print("___________________")
    print("\nCredentials for the user - ",db_name)
    print("Username:",username)
    print("Password:",password)
    print("Host URL:",ENDPOINT)
    print("DB: ",str(final_db_list))
    print("___________________")
    
    cur.close()
    conn.close()

    with open("creds.txt",'a+') as f:
	    f.write("""\n{0},{1},{2},{3}""".format(username,password,ENDPOINT,str(final_db_list)))


except Exception as e:
    print("Exception occured:",e)

print(""""\nStep 2 completed! - {0} is given access to {1}""".format(username,ENDPOINT))


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