import socket
import dns.query
import dns.update
import dns.resolver
import dns.exception
import dns.rcode
import logging
import paramiko

"""
DNS_Failover
Version: 1.0.0
Author: Andreas Günther, github@it-linuxmaker.com
License: GNU General Public License v3.0 or later
"""

zone1="domain1.tld"
zone2="domain2.tld"
mxip1="1.2.3.4"
mxip2="1.2.3.5"
mx1="mx1.example.com"
mx2="mx2.example.com"
record_mx="mx"
record_smtp="smtp"
record_imap="imap"
record_mail="mail"
record_pop3="pop3"
smtp=25
imaps=993
https=443
mysql=3306
ttl=60                              # Short time to life here 60 secs
ns="192.168.0.2"                    # IP address of Bind9-Server
logfile="DNS-Failovertest.log"
space_limit=97
partition="/var/"
user="root"
port1="22"
port2="22"

# Definition of logging
logging.basicConfig(
    filename=logfile, 
    level=logging.DEBUG,
    style="{",
    format="{asctime} [{levelname:8}] [{funcName}] {message}",
    datefmt="%d.%m.%Y %H:%M:%S")

# Function to map Netcat "nc -zv IP-Adresse Port"
def port_check(host, port, timeout=5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return 'open'
    except (socket.timeout, ConnectionRefusedError, socket.gaierror, OSError):
        logging.error(f"The port {port} on the host {host} is not reachable.")
        return None

# Returns the current CNAME for decisions
def get_cname(hostname, nameserver):
    resolver = dns.resolver.Resolver()
    resolver.nameservers = [nameserver]
    try:
        answer = resolver.resolve(hostname, 'CNAME')
        return str(answer[0]).rstrip('.')
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout, dns.exception.DNSException) as e:  
        return None   

# Function to build a connection via ssh
def ssh_connection(host, user, port):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=host, username=user, port=port)
    return client

# Function to checks for existence of the mysql socket
def mysql_socket(host, user, port, count):
    client = ssh_connection(host, user, port)
    try:
        cmd = 'test -S /var/run/mysqld/mysqld.sock && echo "OK"'
        stdin, stdout, stderr = client.exec_command(cmd)
        output = stdout.read().decode().strip()
        if output == "OK":
            logging.info(f"MySQL socket at {host} is present and accessible.")
        else:
            count +=1
            logging.error(f"The MySQL socket failed on host {host}.")    
        return count
    finally:
        client.close()  

# Function fetchDiskUsage checks the available disk space
def fetchDiskUsage(host, user, port, partition, count, space_limit):    
    client = ssh_connection(host, user, port)
    try:
        cmd = f"df -P {partition} | awk 'NR==2 {{gsub(\"%\", \"\", $5); print $5}}'"
        stdin, stdout, stderr = client.exec_command(cmd)
        output = stdout.read().decode().strip()
        usage_percent = int(output)
        if usage_percent < space_limit:
            logging.info(f"The available space on partition {partition} on {host} is currently at {usage_percent} usage percent.")
        else:
            count +=1
            logging.error(f"The available space on partition {partition} on {host} with {usage_percent} is too low.")  
        return count
    finally:
        client.close()                                   

# Function service_availability checks the connection to the requested service
def service_availability(mxip, port, count, service, record, zone, failovermx, nameserver):
    if port_check(mxip,port) == "open":
        logging.info(f"The {service} service is accessible on host {mxip}.")
    else:
        count += 1
        logging.error(f"The {service} service failed on host {mxip}.")
        logging.info(f"The CNAME record on {ns} is updated to {record}.{zone} CNAME {failovermx}!")
        return count

# Runs nsupdate, in this function, for at least two zones that have different records.
def nsupdate_cnames(ns, ttl, actualmx, zone1, records_zone1, zone2, records_zone2):
    if not actualmx.endswith('.'):
        actualmx += '.'

    logging.info(f"NS-Server: {ns}")
    logging.info(f"TTL: {ttl}")
    logging.info(f"Target-CNAME: {actualmx}")
    logging.info(f"Zone 1: {zone1}, Records: {records_zone1}")
    logging.info(f"Zone 2: {zone2}, Records: {records_zone2}")


    # Zone 1
    update = dns.update.Update(zone1)
    logging.info(f"Preparing update for zone: {zone1}")
    for record in records_zone1:
        fqdn = f"{record}.{zone1}."
        logging.info(f" - Updating CNAME {fqdn} to {actualmx}")
        update.delete(fqdn, 'CNAME')
        update.add(fqdn, ttl, 'CNAME', actualmx)

    logging.info(f"Sending update to {ns} for zone {zone1}...")
    try:
        response = dns.query.tcp(update, ns, timeout=5)
        rcode = response.rcode()
        logging.info(f"Response for {zone1}: {dns.rcode.to_text(rcode)}")
        if rcode != 0:
            logging.error(f"Error updating zone {zone1}")
            return False
    except dns.exception.DNSException as e:
        logging.error(f"Exception while updating {zone1}: {e}")
        return False

    # Zone 2
    update2 = dns.update.Update(zone2)
    logging.info(f"Preparing update for zone: {zone2}")
    for record in records_zone2:
        fqdn = f"{record}.{zone2}."
        logging.info(f" - Updating CNAME {fqdn} to {actualmx}")
        update2.delete(fqdn, 'CNAME')
        update2.add(fqdn, ttl, 'CNAME', actualmx)

    print(f"Sending update to {ns} for zone {zone2}...")
    try:
        response2 = dns.query.tcp(update2, ns, timeout=5)
        rcode2 = response2.rcode()
        logging.info(f"Response for {zone2}: {dns.rcode.to_text(rcode2)}")
        if rcode2 != 0:
            logging.error(f"Error updating zone {zone2}")
            return False
    except dns.exception.DNSException as e:
        logging.error(f"Exception while updating {zone2}: {e}")
        return False

    logging.info(f"DNS update finished successfully!")
    return True              

def main():
    logging.info(f"==== Start DNS-Failover ====")
    # Availability tests of the two hosts for the services SMTP, IMAPs and HTTPs. 
    # The existence of the MySQL socket and the storage capacity of the partition are also checked.
    # The goal is that as soon as one of the services on Mailserver1 fails, Mailserver2 takes over completely.
    # The counter count1 reflects the state of mail server 1, analogous to the counter count2.
    count1=0
    count2=0
    service_smtp1 = service_availability(mxip1, smtp, count1, "SMTP", record_smtp, zone1, mx2, ns)
    if service_smtp1:
        count1 = service_smtp1
    service_smtp2 = service_availability(mxip2, smtp, count2, "SMTP", record_smtp, zone1, mx1, ns)
    if service_smtp2:
        count2 = service_smtp2
    service_imap1 = service_availability(mxip1, imaps, count1, "IMAPs", record_imap, zone1, mx2, ns)
    if service_imap1:
        count1 = service_imap1
    service_imap2 = service_availability(mxip2, imaps, count2, "IMAPs", record_imap, zone1, mx1, ns)
    if service_imap2:
        count2 = service_imap2
    service_https1 = service_availability(mxip1, https, count1, "HTTPs", record_mail, zone1, mx2, ns)
    if service_https1:
        count1 = service_https1
    service_https2 = service_availability(mxip2, https, count2, "HTTPs", record_mail, zone1, mx1, ns)
    if service_https2:
        count2 = service_https2         
    service_mysql = service_availability(mxip1, mysql, count1, "MySQL", record_mail, zone1, mx2, ns)  
    if service_mysql:  
        count1 = service_mysql
    service_mysql2 = service_availability(mxip2, mysql, count2, "MySQL", record_mail, zone1, mx1, ns)
    if service_mysql2:
        count2 = service_mysql2

    mysql_socket1 = mysql_socket(mxip1, user, port1, count1)
    if mysql_socket1:
        count1 = mysql_socket1
    mysql_socket2 = mysql_socket(mxip2, user, port2, count2)
    if mysql_socket2:
        count2 = mysql_socket2

    disk_usage1 = fetchDiskUsage(mxip1, user, port1, partition, count1, space_limit)
    if disk_usage1:
        count1 = disk_usage1
    disk_usage2 = fetchDiskUsage(mxip2, user, port2, partition, count2, space_limit)
    if disk_usage2:
        count1 = disk_usage2        

    # Decision logic about which host has failed and should be replaced by the other host.
    # Host 1 is the default state and must be restored after a DNS failover if reachable.    

    records_zone1 = [record_mx, record_smtp, record_imap, record_mail, record_pop3]
    records_zone2 = [record_smtp, record_imap, record_mail, record_pop3]

    if count1 == 0 and count2 == 0:
        if get_cname(f"{record_mx}.{zone1}", ns) == mx2:
            logging.info(f"{mx1} is online, but CNAME still points to {mx2}")
            logging.info(f"Running nsupdate_cnames to {mx1}")
            nsupdate_cnames (ns, ttl, mx1, zone1, records_zone1, zone2, records_zone2)

    else:   
        if count1 != 0:
            print (f"{mx1} ist offline!")
            if get_cname(f"{record_mx}.{zone1}", ns) != mx2:
                logging.info(f"{mx1} is offline, but CNAME still points to {record_mx}.{zone1}")
                logging.info(f"Running nsupdate_cnames to {mx2}")
                nsupdate_cnames (ns, ttl, mx2, zone1, records_zone1, zone2, records_zone2)
        else:
            if count2 != 0:
                print (f"{mx2} ist offline!")
                if get_cname(f"{record_smtp}.{zone1}", ns) == mx2:
                    logging.info(f"{mx2} is offline, but CNAME still points to {record_smtp}.{zone1}")
                    logging.info(f"Running nsupdate_cnames to zu {mx1}")
                    nsupdate_cnames (ns, ttl, mx1, zone1, records_zone1, zone2, records_zone2)

    logging.info(f"==== DNS-Failover has been completed ====")                   

# Main programm
if __name__ == "__main__":
    main()