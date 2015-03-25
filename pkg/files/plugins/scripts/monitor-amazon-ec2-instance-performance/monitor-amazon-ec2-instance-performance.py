#!/usr/bin/python

import sys
import os
import os.path
import boto
import boto.ec2
import boto.ec2.cloudwatch
import boto.regioninfo
import datetime

from boto.exception import BotoServerError

AWS_ACCESS_KEY = os.environ.get('UPTIME_AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.environ.get('UPTIME_AWS_SECRET_KEY')
UPTIME_HOSTNAME = os.environ.get('UPTIME_HOSTNAME')

EC2_STATUS = {"running": 0, "shutting-down":1, "stopping":2, "pending":3, "terminated":4, "stopped":5}
EC2_METRICS = ['CPUUtilization', 'DiskReadBytes', 'DiskReadOps', 'DiskWriteBytes', 'DiskWriteOps', 'NetworkIn', 'NetworkOut']

class Error(Exception):
    pass

def main(argv):
	#check for config file.
	if os.path.exists("boto.config"):
		f = open('boto.config', 'r')
		
		for line in f:
			templine=line.rstrip().split("=")
			if (templine[0] == 'proxy'):
				PROXY=templine[1]
			elif (templine[0] == 'proxy_port'):
				PROXY_PORT=templine[1]
			elif (templine[0] == 'proxy_user'):
				PROXY_USER=templine[1]
			elif (templine[0] == 'proxy_pass'):
				PROXY_PASSWORD=templine[1]			
			elif (templine[0] == 'endpoint'):
				ENDPOINT=templine[1]
			elif (templine[0] == 'endpoint_name'):
				ENDPOINT_NAME=templine[1]
			elif (templine[0] == 'region'):
				REGION=templine[1]
		f.close()
	# Validate if proxy settings are set or not
	try:
		PROXY
		PROXY_PORT
		PROXY_USER
		PROXY_PASSWORD
	except NameError:
		PROXY_SET=0
	else:
		PROXY_SET=1
	
	#Set to use default region of us-east-1
	ENDPOINT_REGION=0
	
	#test to see if there was an endpoint name set if not use endpoint as a name
	try:
		ENDPOINT_NAME
	except NameError:
		ENDPOINT_NAME = "ENDPOINT"
	
	#Test for endpoint if set then update flag for later use as well as set region info for cloudwatch
	try:
		ENDPOINT
	except NameError:
		ENDPOINT_REGION=0
	else: 
		ENDPOINT_REGION=1
		region2 = boto.regioninfo.RegionInfo(name=ENDPOINT_NAME, endpoint=ENDPOINT)
	
	# test for region and if set enable the 2 regions to use for EC2 and Cloudwatch. This will override endpoint if both set.
	try:
		REGION
	except NameError:
		ENDPOINT_REGION=ENDPOINT_REGION
	else:
		ENDPOINT_REGION=2
		region1 = boto.ec2.get_region(REGION, aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
		for r in boto.ec2.cloudwatch.regions():
			if (r.name == REGION):
				region2 = r
	
	
	#boto.set_stream_logger('boto')
	try:
		#Check if using a proxy for EC2 and make approiate connection type based on info provided in config
		if (PROXY_SET == 1):
			if (ENDPOINT_REGION == 0):
				ec2conn = boto.connect_ec2(AWS_ACCESS_KEY, AWS_SECRET_KEY)
			elif (ENDPOINT_REGION == 1):
				ec2conn = boto.connect_ec2_endpoint(ENDPOINT,AWS_ACCESS_KEY, AWS_SECRET_KEY, proxy=PROXY, proxy_port=PROXY_PORT, proxy_user=PROXY_USER, proxy_pass=PROXY_PASSWORD)
			else: 
				ec2conn = boto.connect_ec2(AWS_ACCESS_KEY, AWS_SECRET_KEY, region=region1)
		else:
			if (ENDPOINT_REGION == 0):
				ec2conn = boto.connect_ec2(AWS_ACCESS_KEY, AWS_SECRET_KEY)
			elif (ENDPOINT_REGION == 1):
				ec2conn = boto.connect_ec2_endpoint(ENDPOINT,AWS_ACCESS_KEY, AWS_SECRET_KEY)
			else: 
				ec2conn = boto.connect_ec2(AWS_ACCESS_KEY, AWS_SECRET_KEY, region=region1)
		
		#Get instance info
		reservations = ec2conn.get_all_instances(instance_ids=[UPTIME_HOSTNAME])
		instance = reservations[0].instances[0]

		# if instance is running then get metrics
		if instance.state == "running":
			try:	
				#Check proxy info for cloudwatch as well as other connection settings and connect
				if (PROXY_SET == 1):
					if (ENDPOINT_REGION == 0):
						c = boto.connect_cloudwatch(AWS_ACCESS_KEY, AWS_SECRET_KEY, proxy=PROXY, proxy_port=PROXY_PORT, proxy_user=PROXY_USER, proxy_pass=PROXY_PASSWORD)
					else: 
						c = boto.connect_cloudwatch(AWS_ACCESS_KEY, AWS_SECRET_KEY, region=region2, proxy=PROXY, proxy_port=PROXY_PORT, proxy_user=PROXY_USER, proxy_pass=PROXY_PASSWORD)
				else:
					if (ENDPOINT_REGION == 0):
						c = boto.connect_cloudwatch(AWS_ACCESS_KEY, AWS_SECRET_KEY)
					else: 
						c = boto.connect_cloudwatch(AWS_ACCESS_KEY, AWS_SECRET_KEY, region=region2)
				#set the start and end times for getting metrics. Current time and 1 hour ago.
				end = datetime.datetime.now()
				start = end - datetime.timedelta(hours=1)
				
				# Retrieve metrics 
				for j in range(len(EC2_METRICS)):
					stats = c.get_metric_statistics(
						60, 
						start, 
						end, 
						EC2_METRICS[j], 
						'AWS/EC2', 
						'Average', 
						{'InstanceId' : instance.id}
					)
					if stats:
						print EC2_METRICS[j],
						print stats[len(stats)-1]['Average']	# get last reading
					else:
						print "Warning: No performance metrics found. Content of stats:",
						print stats
						sys.exit(1)
			except BotoServerError as serverErr:
				print "Error: Cannot connect to CloudWatch. Check your credentials and/or access to ec2.amazonaws.com on port 443."
				sys.exit(2)
		else:
			print "Error: Instance is not running. Instance state is:",
			print instance.state
			sys.exit(2)
	except BotoServerError as serverErr:
		print "Error: Cannot connect to EC2.  Check your credentials and/or access to ec2.amazonaws.com on port 443."
		sys.exit(2)		

if __name__ == "__main__":
	main(sys.argv[1:])
	sys.exit(0)