#!/usr/bin/python

import sys
import os
import boto
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
	try:
		ec2conn = boto.connect_ec2(AWS_ACCESS_KEY, AWS_SECRET_KEY)
		reservations = ec2conn.get_all_instances(instance_ids=[UPTIME_HOSTNAME])
		instance = reservations[0].instances[0]

		if instance.state == "running":
			try:
				c = boto.connect_cloudwatch(AWS_ACCESS_KEY, AWS_SECRET_KEY)
				end = datetime.datetime.now()
				start = end - datetime.timedelta(hours=1)
				
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