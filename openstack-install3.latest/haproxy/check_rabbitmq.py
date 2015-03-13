#!/usr/bin/python
from amqplib import client_0_8 as amqp
import sys, re

userid="guest"
password="guest"
virtual_host="/"
def data_receieved(msg):
     print 'Received: ' + msg.body
with open("/etc/rabbitmq/rabbitmq.config", "r") as file_hd:
  for a_line in file_hd:
	if re.search(r'^#', a_line):
		continue
	if re.search(r'tcp_listeners', a_line):
		rabbit_port=re.sub("\D", "", a_line.split()[1])
	if re.search(r'default_user', a_line):
		userid=re.sub("[\W_]+", "", a_line.split()[1])
        if re.search(r'default_password', a_line):
                password=re.sub("[\W_]+", "", a_line.split()[1])
        if re.search(r'default_vhost', a_line):
                virtual_host=re.sub("\<<|\>>|\"", "", a_line.split()[1])
file_hd.close()

try:
	amqp_url="localhost:"+rabbit_port
	lConnection = amqp.Connection(host=amqp_url, userid=userid, password=password, virtual_host=virtual_host, insist=False)
	lChannel = lConnection.channel()
	lMessage = amqp.Message("Are you there?")
	lMessage.properties["delivery_mode"] = 2
	lChannel.queue_declare(queue="health_check_queue", durable=True, exclusive=False, auto_delete=False)

	#Create an exchange.  Exchanges public messages to queues  
	# durable and auto_delete are the same as for a queue.
	# type indicates the type of exchange we want - valid values are fanout, direct, topic
	lChannel.exchange_declare(exchange="health_check_exchange", type="direct", durable=True, auto_delete=False)

	# Tie the queue to the exchange.  Any messages arriving at the specified exchange 
	# are routed to the specified queue, but only if they arrive with the routing key specified
	lChannel.queue_bind(queue="health_check_queue", exchange="health_check_exchange", routing_key="Test")
	lChannel.basic_publish(lMessage, exchange="health_check_exchange", routing_key="Test")
	# Connect the queue to the callback function
	# no_ack defaults to false.  Setting this to true means that the client will acknowledge receipt
	# of the message to the server.  The message will be sent again if it isn't acknowledged.
	lChannel.basic_consume(queue='health_check_queue', no_ack=True, callback=data_receieved, consumer_tag="TestTag")
	#unregister the message notification callback
	# never called in this example, but this is how you do it.
except Exception as e:
	print "HTTP/1.1 503 Service Unavailable"
	print "Content-Type: Content-Type: text/plain"
	print
	print str(e)
	sys.exit(STATE_CRITICAL)

lChannel.basic_cancel("TestTag")
lChannel.close()
lConnection.close()
print "HTTP/1.1 200 OK"
print "Content-Type: Content-Type: text/plain"
print
print "Rabbitmq checked!"
