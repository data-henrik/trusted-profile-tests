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

codeversion='1.2.0'

# load .env if present
load_dotenv()


API_TOKEN=os.getenv('API_TOKEN')

# see https://cloud.ibm.com/apidocs/iam-identity-token-api#gettoken-crtoken
def retrieveIAMTokenforCR(tpname, crtoken):
    url     = "https://iam.cloud.ibm.com/identity/token"
    headers = { "Content-Type" : "application/x-www-form-urlencoded" }
    data    = {"profile_name": tpname, "grant_type":"urn:ibm:params:oauth:grant-type:cr-token", "cr_token":crtoken}
    response  = requests.post( url, headers=headers, data=data )
    return response.json()


# Read the service account token from file
def readSAToken(filename):
    token = None
    try:
        with open(filename) as token_file:
            token = token_file.readlines()
        return token
    except:
        # error handled by caller
        return token

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
    crtoken=readSAToken(f'/var/run/secrets/tokens/sa-token')
    if crtoken is None:
        return jsonify(message="error reading service account token")
        exit
    authTokens=retrieveIAMTokenforCR(trustedprofile_name, crtoken)
    if 'access_token' in authTokens:
        iam_token=authTokens["access_token"]
        return jsonify(message="resource instances", crtoken=crtoken, tokens=authTokens, resource_instances=getResourceInstances(iam_token))
    else:
        return jsonify(message=authTokens)



# Start the actual app
# Get the PORT from environment
port = os.getenv('PORT', '5000')
if __name__ == "__main__":
	app.run(host='0.0.0.0',port=int(port))


