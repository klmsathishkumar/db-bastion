import pandas as pd
path = "creds_data.csv"
data = pd.read_csv(path)
data = data.iloc[20:236,:]
db_creds = {}
size = data.shape[0]
for i in range(size):
    username = data.iloc[i]["Username"]
    details = data.iloc[i][3:6]
    if username in db_creds:
        db_creds[username].append(details)
    else:
        db_creds[username] = [details]

f = open('text_message.txt', 'r+')
f.truncate(0)

prefix = """Hello , Here are your individual credentials for the production databases,
"""

body = """
Endpoint: {0}
DB Name: {1}
Username: {2}
Password: {3}

"""

one_suffix = """
You have been provided with full read access for the above database.

For steps to connect to the database via SSM, check this documentation: https://fourkites.atlassian.net/wiki/spaces/DEV/pages/16594600060/AWS+Prod+DB+Bastion+-+Steps+to+connect.
If any issue in connecting to SSM and accessing the DB, kindly ping me. Thanks



"""

many_suffix = """
You have been provided with full read access for all the above databases.

For steps to connect to the database via SSM, check this documentation: https://fourkites.atlassian.net/wiki/spaces/DEV/pages/16594600060/AWS+Prod+DB+Bastion+-+Steps+to+connect.
If any issue in connecting to SSM and accessing the DB, kindly ping me. Thanks


"""

for username in db_creds:
    count = 0
    print("\nGenerating message for {}".format(username))
    details = db_creds[username]
    with open("text_message.txt",'a+') as f:
        f.write(prefix)
    for db in details:
        password,db_name,hostname = db
        text = body.format(hostname,db_name,username,password)
        print("\n{} is completed...".format(username))
        count += 1
        with open("text_message.txt",'a+') as f:
	        f.write(text)
    if count > 1:
        with open("text_message.txt",'a+') as f:
            f.write(many_suffix)
    else:
        with open("text_message.txt",'a+') as f:
            f.write(one_suffix)



