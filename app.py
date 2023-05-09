# Test Trusted Profiles with Compute Resources
#
# The code demonstrates how a simple REST API can be developed and
# then deployed as serverless app to IBM Cloud Code Engine.
#
# See the README and related tutorial for details.
#
# Written by Henrik Loeser (data-henrik), hloeser@de.ibm.com
# (C) 2023 by IBM

import flask, os, datetime, decimal, re, requests, time
# everything Flask for this app
from flask import (Flask, jsonify, make_response, redirect,request,
		   render_template, url_for, Response, stream_with_context)
import json
from dotenv import load_dotenv
from ibm_cloud_sdk_core.authenticators import ContainerAuthenticator
from ibm_cloud_sdk_core import ApiException
from ibmcloudant.cloudant_v1 import CloudantV1, Document
from urllib.parse import urljoin

codeversion='2.2.5'

# load .env if present
load_dotenv()


API_TOKEN=os.getenv('API_TOKEN')

def readCloudantDocs(tpname):
    # Create the authenticator.
    try: 
        cr_token_fname=os.getenv("TEST_TOKEN_FNAME","/var/run/secrets/tokens/sa-token")
        crauthenticator = ContainerAuthenticator(iam_profile_name=tpname, cr_token_filename=cr_token_fname)
        # 1. Create a client with `CLOUDANT` default service name =============
        client = CloudantV1(authenticator=crauthenticator)
        client.set_service_url("some-hardcoded-uri")
        response = client.get_all_dbs().get_result()
        return response
    except:
        return "error retrieving credentials"

def readCloudantDocs2(tpname, endpoint):
    try: 
        # Decide on which file to use. Are we testing locally?
        cr_token_fname=os.getenv("TEST_TOKEN_FNAME","/var/run/secrets/tokens/sa-token")
        # Create the container authenticator
        crauthenticator = ContainerAuthenticator(iam_profile_name=tpname, cr_token_filename=cr_token_fname)

        # Create a Cloudant service based on the authenticator
        client = CloudantV1(authenticator=crauthenticator)
        # Set the endpoint URL
        client.set_service_url(endpoint)
        # Fetch the list of databases managed by the service
        response = client.get_all_dbs().get_result()
        # All done, return the result
        return response
    except ApiException as ae:
        print("Method failed")
        print(" - status code: " + str(ae.code))
        print(" - error message: " + ae.message)
        if ("reason" in ae.http_response.json()):
            print(" - reason: " + ae.http_response.json()["reason"])
    except:
        return "error retrieving credentials"


# see https://cloud.ibm.com/apidocs/iam-identity-token-api#gettoken-crtoken
def retrieveIAMTokenforCR(tpname, crtoken):
    url     = "https://iam.cloud.ibm.com/identity/token"
    headers = { "Content-Type" : "application/x-www-form-urlencoded" }
    data    = {"profile_name": tpname, "grant_type":"urn:ibm:params:oauth:grant-type:cr-token", "cr_token":crtoken}
    response  = requests.post( url, headers=headers, data=data )
    return response.json()


# Read the service account token from file
def readSAToken():
    # allow to overwrite or provide the token, e.g., for local testing
    filename=os.getenv("TEST_TOKEN_FNAME","/var/run/secrets/tokens/sa-token")
    try:
        with open(filename) as token_file:
            token = token_file.readlines()
        return token
    except:
        # error handled by caller
        return None
    
# fetch from API and perform necessary paging
def handleAPIAccess(url, headers, payload, next_field, result_field):
    # fetch data from API function, passing headers and parameters
    response = requests.get(url, headers=headers, params=payload)
    data=response.json()
    curr_response=response.json()
    # check for paging field and, if necessary, page through all results sets
    # we need to make sure to only move ahead if the next field is present and non-empty
    while (str(next_field) in curr_response and curr_response[str(next_field)] is not None):

        if curr_response[str(next_field)].startswith("https"):
            # fetch next result page if full URL present
            response = requests.get(curr_response[str(next_field)], headers=headers)
        else:
            # only a partial URL present, construct it from the base and the new path
            newurl = urljoin(url, curr_response[str(next_field)])
            response = requests.get(newurl, headers=headers)
        curr_response=response.json()
        # extend the set of retrieved objects
        data[str(result_field)].extend(curr_response[str(result_field)])
    return data


# see https://cloud.ibm.com/apidocs/resource-controller/resource-controller#list-resource-instances
def getResourceInstances(iam_token):
    url = f'https://resource-controller.cloud.ibm.com/v2/resource_instances'
    headers = { "Authorization" : "Bearer "+iam_token }
    payload = { "limit": 100}
    return handleAPIAccess(url, headers, payload, "next_url", "resources")


# Initialize Flask app
app = Flask(__name__)

# for testing
@app.route('/', methods=['GET'])
def index():
    return jsonify(result="ok", codeversion=codeversion)

@app.route('/api/listresources', methods=['GET'])
def listresources():
    trustedprofile_name=request.args.get('tpname', 'TPTest')
    crtoken=readSAToken()
    if crtoken is None:
        return jsonify(message="error reading service account token")
        exit
    authTokens=retrieveIAMTokenforCR(trustedprofile_name, crtoken)
    if 'access_token' in authTokens:
        iam_token=authTokens["access_token"]
        return jsonify(message="resource instances", crtoken=crtoken, tokens=authTokens, resource_instances=getResourceInstances(iam_token))
    else:
        return jsonify(message=authTokens)

@app.route('/api/cloudantdbs', methods=['GET'])
def listdbs():
    trustedprofile_name=request.args.get('tpname', 'TPTest')
    return jsonify(readCloudantDocs(trustedprofile_name))

@app.route('/api/cloudantdbs2', methods=['GET'])
def listdbs2():
    trustedprofile_name=request.args.get('tpname', 'TPTest')
    cloudant_name=request.args.get('cloudantname', 'Cloudant')
    crtoken=readSAToken()
    if crtoken is None:
        return jsonify(message="error reading service account token")
        exit
    authTokens=retrieveIAMTokenforCR(trustedprofile_name, crtoken)
    if 'access_token' in authTokens:
        iam_token=authTokens["access_token"]
        print("got IAM access token")
        resource_instances=getResourceInstances(iam_token)
        endpoint_url=None
        for resource in resource_instances['resources']:
            if resource['name']==cloudant_name:
                endpoint_url=resource['extensions']['endpoints']['public']
                print("endpoint ", endpoint_url)
        return jsonify(readCloudantDocs2(trustedprofile_name,'https://'+endpoint_url))
    else:
        return jsonify(message=authTokens)
    


# Start the actual app
# Get the PORT from environment
port = os.getenv('PORT', '5000')
if __name__ == "__main__":
	app.run(host='0.0.0.0',port=int(port))


