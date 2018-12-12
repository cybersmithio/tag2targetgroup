#!/usr/bin/python
#
# Takes a Tenable.io asset data and generates a CSV report.
# The output file is called tio-asset-download.csv
#
# Example usage with environment variables:
# export TIO_ACCESS_KEY="********************"
# export TIO_SECRET_KEY="********************"
# ./tio-asset-download.py
#
# This script requires the Tenable.io Python SDK to be installed.
# If this is not already done, then run pip install tenable_io
#
# Requires the following:
#   pip install tenable_io ipaddr netaddr

import json
import os
import csv
import sys
import time
from tenable_io.client import TenableIOClient
import argparse
import netaddr
import ipaddr

#Right now, host and port are ignored
def DownloadAssetList(DEBUG,accesskey,secretkey,host,port,tagname,tagvalue,targetgroup,limitsubnet,action):
    if limitsubnet == "":
        LIMITSUBNET=False
        if DEBUG:
            print("All IP addresses from each matching asset will be added to the target group")
    else:
        LIMITSUBNET=True
        subnetrange=[]
        #Split up limitsubnet string by commas into multiple IP ranges
        iplist = limitsubnet.split(',')

        # Check if the IP address is an IP range (instead of a single IP or CIDR)
        for j in iplist:
            # Check if the IP address is an IP range (instead of a single IP or CIDR)
            hyphen = j.find("-")
            if (hyphen >= 0):
                # If the IP address is a range, convert it to CIDR notation
                # print "CIDRs",netaddr.iprange_to_cidrs(j[0:hyphen],j[hyphen+1:])
                for k in netaddr.iprange_to_cidrs(j[0:hyphen], j[hyphen + 1:]):
                    if DEBUG:
                        print("Adding "+str(k)+" to the subnets to limit by")
                    subnetrange.append(k)
            else:
                subnetrange.append(j)
                if DEBUG:
                    print("Adding " + str(j) + " to the subnets to limit by")

    #Create the connection to Tenable.io
    client = TenableIOClient(access_key=accesskey, secret_key=secretkey)

    #Gather the list of assets
    resp=client.post("assets/export",{"chunk_size": "1000"})
    respdata=json.loads(resp.text)

    exportuuid=str(respdata['export_uuid'])
    print("Export UUID: "+exportuuid)


    #Gather the list of assets
    result="NOT"
    while result != "FINISHED":
        resp=client.get("assets/export/"+exportuuid+"/status")
        respdata=json.loads(resp.text)
        result=str(respdata['status'])
        print("Export status:"+result)
        time.sleep(1)

    chunks = respdata['chunks_available']

    #The IP addresses going into the target group
    tgaddresses=""

    #Start iterating through the chunks and download.
    for i in chunks:
        if DEBUG:
            print("Downloading chunk "+str(i))

        resp=client.get("assets/export/"+exportuuid+"/chunks/"+str(i))
        respdata=json.loads(resp.text)

        #Loop through all the downloaded assets, parse the values, and match based on the tag.
        for i in respdata:
            #Break out fields with multiple values into a multi-line cell
            os = '\n'.join(i['operating_systems'])
            ipv4 = '\n'.join(i['ipv4s'])
            ipv6 = '\n'.join(i['ipv6s'])
            netbios_name = '\n'.join(i['netbios_names'])
            fqdn = '\n'.join(i['fqdns'])
            mac = '\n'.join(i['mac_addresses'])
            id=i['id'] if 'id' in i else ''
            last_seen=i['last_seen'] if 'last_seen' in i else ''
            sources=i['sources'] if 'sources' in i else ''
            try:
                if i['has_agent'] == "TRUE":
                    agent=True
                else:
                    agent=False
            except:
                agent=False

            #Now process the data for this asset
            for j in i['tags']:
                if DEBUG:
                    print("Tags:",j)
                if j['key'] == tagname:
                    if DEBUG:
                        print("Asset ID "+str(id)+" has a tag matching "+str(tagname))
                    if j['value'] == tagvalue:
                        if DEBUG:
                            print("\n\n\nAsset ID " + str(id) + " tag value matches " + str(tagvalue))
                            print("This asset should be in the target group")

                        #Add IP addresses to the target group
                        if LIMITSUBNET:
                            #Only add IP addresses to the target group that are within the subnet range
                            for k in subnetrange:
                                n1 = ipaddr.IPNetwork(k)
                                for m in i['ipv4s']:
                                    n2= ipaddr.IPNetwork(m)
                                    if n2.overlaps(n1):
                                        if DEBUG:
                                            print("The address "+str(n2)+" overlaps with "+str(n1)+" so "+str(m)+" it should be added to the target group.")
                                        tgaddresses = tgaddresses + str(m) + ","
                                    else:
                                        if DEBUG:
                                            print("The address "+str(n2)+" does not overlap with "+str(n1)+" so "+str(m)+" is not being added to the target group.")

                        else:
                            #Add all IP addresses from this host to the target group
                            for k in i['ipv4s']:
                                tgaddresses=tgaddresses+str(k)+","
                                if DEBUG:
                                    print("Adding "+str(k)+" to the target group.")
                            for k in i['ipv6s']:
                                tgaddresses=tgaddresses+str(k)+","
                                if DEBUG:
                                    print("Adding "+str(k)+" to the target group.")

    print("The final target group member list is: "+tgaddresses)
    if action == "overwrite":
        UpdateTargetGroup(DEBUG,client,targetgroup,tgaddresses)
    elif action == "append":
        AppendTargetGroup(DEBUG, client, targetgroup, tgaddresses)
    return(True)


def GetTargetGroupByName(DEBUG,client,targetgroup):
    if DEBUG:
        print("Finding Target Group ID of target group named "+str(targetgroup))

    resp = client.get("target-groups")
    respdata = json.loads(resp.text)
    for i in respdata['target_groups']:
        if i['name'] == targetgroup:
            if DEBUG:
                print("Found the target group ID: ",i['id'])
            return([i['id'],i['members']])
    return(False)

def AppendTargetGroup(DEBUG,client,targetgroup,tgaddresses):
    if DEBUG:
        print("Appending the new addresses to the target group of "+str(targetgroup))

    tg=GetTargetGroupByName(DEBUG,client,targetgroup)
    if not tg:
        if DEBUG:
            print("Target group not found. Creating a new one instead of appending")
        resp=client.post("target-groups",{"name": targetgroup,"members": str(tgaddresses), "type": "system"})
        respdata=json.loads(resp.text)
        if DEBUG:
            print("Response when attempting to create target group:",respdata)
    else:
        if DEBUG:
            print("Target group exists. Appending members list with new addresses")
            print("Existing member list is: "+str(tg[1]))

        resp=client.put("target-groups/"+str(tg[0]),{"name": targetgroup,"members": str(tg[1])+","+str(tgaddresses), "type": "system"})
        respdata=json.loads(resp.text)
        if DEBUG:
            print("Response when attempting to create target group:",respdata)




def UpdateTargetGroup(DEBUG,client,targetgroup,tgaddresses):
    if DEBUG:
        print("Replacing the target group members of "+str(targetgroup)+" with new addresses")

    tg=GetTargetGroupByName(DEBUG,client,targetgroup)
    if not tg:
        if DEBUG:
            print("Target group not found. Creating a new one.")
        resp=client.post("target-groups",{"name": targetgroup,"members": str(tgaddresses), "type": "system"})
        respdata=json.loads(resp.text)
        if DEBUG:
            print("Response when attempting to create target group:",respdata)
    else:
        if DEBUG:
            print("Target group exists. Updating members list with new list")
        resp=client.put("target-groups/"+str(tg[0]),{"name": targetgroup,"members": str(tgaddresses), "type": "system"})
        respdata=json.loads(resp.text)
        if DEBUG:
            print("Response when attempting to create target group:",respdata)



######################
###
### Program start
###
######################

# Get the arguments from the command line
parser = argparse.ArgumentParser(description="Pulls a list of assets from Tenable.io based on tags, and then creates a target group.")
parser.add_argument('--tagname',help="Look for assets with this tag name.",nargs=1,action="store",required=True)
parser.add_argument('--tagvalue',help="Look for assets with this tag value attached to the tag name",nargs=1,action="store",required=True)
parser.add_argument('--targetgroup',help="Put the assets into this target group",nargs=1,action="store",required=True)
parser.add_argument('--limitsubnet',help="If the assets have multiple IP addresses, this will limit the addresses put into the target group to a certain subnet.",nargs=1,action="store")
parser.add_argument('--accesskey',help="The Tenable.io access key",nargs=1,action="store")
parser.add_argument('--secretkey',help="The Tenable.io secret key",nargs=1,action="store")
parser.add_argument('--host',help="The Tenable.io host. (Default is cloud.tenable.com)",nargs=1,action="store")
parser.add_argument('--port',help="The Tenable.io port. (Default is 443)",nargs=1,action="store")
parser.add_argument('--debug',help="Turn on debugging",action="store_true")
parser.add_argument('--append',help="For whatever asset IP addresses match, just append their IP addresses to the existing group membership.",action="store_true")

args=parser.parse_args()

DEBUG=False

if args.debug:
    DEBUG=True
    print("Debugging is enabled.")



# Pull as much information from the environment variables
# as possible, and where missing then initialize the variables.
if os.getenv('TIO_ACCESS_KEY') is None:
    accesskey = ""
else:
    accesskey = os.getenv('TIO_ACCESS_KEY')

# If there is an access key specified on the command line, this override anything else.
try:
    if args.accesskey[0] != "":
        accesskey = args.accesskey[0]
except:
    nop = 0


if os.getenv('TIO_SECRET_KEY') is None:
    secretkey = ""
else:
    secretkey = os.getenv('TIO_SECRET_KEY')


# If there is an  secret key specified on the command line, this override anything else.
try:
    if args.secretkey[0] != "":
        secretkey = args.secretkey[0]
except:
    nop = 0


try:
    if args.host[0] != "":
        host = args.host[0]
except:
    host = "cloud.tenable.com"

try:
    if args.port[0] != "":
        port = args.port[0]
except:
    port = "443"

try:
    if args.tagname[0] != "":
        tagname=args.tagname[0]
except:
    tagname=""

try:
    if args.tagvalue[0] != "":
        tagvalue=args.tagvalue[0]
except:
    tagvalue=""

try:
    if args.targetgroup[0] != "":
        targetgroup=args.targetgroup[0]
except:
    targetgroup=""

try:
    if args.limitsubnet[0] != "":
        limitsubnet=args.limitsubnet[0]
except:
    limitsubnet=""


action="overwrite"

if args.append:
    action="append"
    print("Append mode")



print "Connecting to cloud.tenable.com with access key",accesskey,"to report on assets"

#Download the asset list, and then build the target group
DownloadAssetList(DEBUG,accesskey,secretkey,host,port,tagname,tagvalue,targetgroup,limitsubnet,action)


