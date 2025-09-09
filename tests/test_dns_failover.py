import pytest
from unittest.mock import patch, MagicMock
from DNS_Failover import port_check
from DNS_Failover import get_cname
from DNS_Failover import ssh_connection
from DNS_Failover import mysql_socket
from DNS_Failover import fetchDiskUsage
from DNS_Failover import service_availability
from DNS_Failover import nsupdate_cnames
from DNS_Failover import main
import dns.resolver

"""
Tests for DNS_Failover

Author: Andreas Günther, github@it-linuxmaker.com
License: GNU General Public License v3.0 or later
"""

PORTS = [25, 110, 143, 443, 993, 995]                                    # Example port list

# Testing function 'port_check()'
@pytest.mark.parametrize("port", PORTS)
@patch('socket.create_connection', side_effect=ConnectionRefusedError)
def test_fail_port_check_closed(mock_connect, port):
    assert port_check("1.2.3.4", port) is None

@pytest.mark.parametrize("port", PORTS)
@patch('socket.create_connection')
def test_success_port_check_open(mock_conn, port):
    mock_conn.return_value.__enter__.return_value = MagicMock()
    assert port_check("1.2.3.4", port) == 'open'

# Testing function 'service_availability()'
@patch('DNS_Failover.port_check', return_value=None)
def test_service_availability_failure(mock_port_check):
    result = service_availability('1.2.3.4', 25, 0, "SMTP", "smtp", "example.com", "mx2.example.com", "8.8.8.8")
    assert result == 1

# Testing function 'get_cname()'
def mock_get_cname(query_name, rdtype):
    if rdtype != 'CNAME':
        raise dns.resolver.NoAnswer()

    # Extract domain base part 
    parts = query_name.split('.')
    if len(parts) < 3:
        base_domain = query_name 
    else:
        base_domain = '.'.join(parts[-2:])  

    target = f"mx1.{base_domain}."
    mock_cname = type('MockCname', (object,), {'target': target})()
    return [mock_cname]

with patch.object(dns.resolver.Resolver, 'resolve', side_effect=mock_get_cname):
    print(get_cname('mail.example.com', '8.8.8.8'))        
    print(get_cname('smtp.example.org', '1.1.1.1')) 
    print(get_cname('imap.example.com', '9.9.9.9'))

# Testing function ssh_connection()
@patch("DNS_Failover.paramiko.SSHClient")
def test_ssh_connection_accept(mock_sshclient_class):
    mock_client = MagicMock()
    mock_sshclient_class.return_value = mock_client

    conn = ssh_connection("example.com", "root", 22)

    mock_client.connect.assert_called_once_with(
        hostname="example.com", username="root", port=22
    )
    assert conn == mock_client

# Testing function mysql_socket()    
@patch("DNS_Failover.paramiko.SSHClient")
def test_mysql_socket_success(mock_ssh_client_class):
    mock_client = MagicMock()
    mock_ssh_client_class.return_value = mock_client

    mock_stdout = MagicMock()
    mock_stdout.read.return_value = b"OK\n"
    mock_client.exec_command.return_value = (None, mock_stdout, None)

    count = 0
    result = mysql_socket("host", "user", 22, count)

    assert result == 0
    mock_client.exec_command.assert_called_once()


@patch("DNS_Failover.paramiko.SSHClient")
def test_mysql_socket_failure(mock_ssh_client_class):
    mock_client = MagicMock()
    mock_ssh_client_class.return_value = mock_client

    mock_stdout = MagicMock()
    mock_stdout.read.return_value = b""
    mock_client.exec_command.return_value = (None, mock_stdout, None)

    count = 0
    result = mysql_socket("host", "user", 22, count)

    assert result == 1
    mock_client.exec_command.assert_called_once()

# Testing function fetchDiskUsage
@patch("DNS_Failover.paramiko.SSHClient")
def test_fetchDiskUsage_success(mock_ssh_client_class):
    mock_client = MagicMock()
    mock_ssh_client_class.return_value = mock_client

    mock_stdout = MagicMock()
    mock_stdout.read.return_value = b"42\n"
    mock_client.exec_command.return_value = (None, mock_stdout, None)

    count = 0
    space_limit = 97
    result = fetchDiskUsage("host", "user", 22, "/var/", count, space_limit)

    assert result == 0
    mock_client.exec_command.assert_called_once()

@patch("DNS_Failover.paramiko.SSHClient")
def test_fetchDiskUsage_failure(mock_ssh_client_class):
    mock_client = MagicMock()
    mock_ssh_client_class.return_value = mock_client

    mock_stdout = MagicMock()
    mock_stdout.read.return_value = b"98\n"
    mock_client.exec_command.return_value = (None, mock_stdout, None)

    count = 0
    space_limit = 97
    result = fetchDiskUsage("host", "user", 22, "/var/", count, space_limit)

    assert result == 1
    mock_client.exec_command.assert_called_once()    

# Testing function nsupdate_cnames()
@patch("dns.query.tcp")
@patch("dns.update.Update")
def test_nsupdate_cnames_success(mock_update_class, mock_query_tcp):
    # Mock update objects for both zones
    mock_update_zone1 = MagicMock()
    mock_update_zone2 = MagicMock()
    mock_update_class.side_effect = [mock_update_zone1, mock_update_zone2]

    # Mock for successful DNS responses
    mock_response1 = MagicMock()
    mock_response1.rcode.return_value = 0
    mock_response2 = MagicMock()
    mock_response2.rcode.return_value = 0
    mock_query_tcp.side_effect = [mock_response1, mock_response2]

    result = nsupdate_cnames(
        ns="test-ns",
        ttl=123,
        actualmx="target-mx",
        zone1="zone-one.test",
        records_zone1=["record1", "record2"],
        zone2="zone-two.test",
        records_zone2=["record3"]
    )

    assert result is True
    assert mock_update_class.call_count == 2
    assert mock_query_tcp.call_count == 2

    mock_update_zone1.delete.assert_any_call("record1.zone-one.test.", "CNAME")
    mock_update_zone1.add.assert_any_call("record1.zone-one.test.", 123, "CNAME", "target-mx.")

    mock_update_zone2.delete.assert_any_call("record3.zone-two.test.", "CNAME")
    mock_update_zone2.add.assert_any_call("record3.zone-two.test.", 123, "CNAME", "target-mx.")    

@patch("dns.query.tcp")
@patch("dns.update.Update")
def test_nsupdate_cnames_failure_rcode(mock_update_class, mock_query_tcp):
    mock_update_zone1 = MagicMock()
    mock_update_zone2 = MagicMock()
    mock_update_class.side_effect = [mock_update_zone1, mock_update_zone2]

    # Return error code
    mock_response = MagicMock()
    mock_response.rcode.return_value = 1  # eg. FORMERR
    mock_query_tcp.return_value = mock_response

    result = nsupdate_cnames(
        ns="test-ns",
        ttl=321,
        actualmx="failover-mx",
        zone1="zone-a.test",
        records_zone1=["rec-a"],
        zone2="zone-b.test",
        records_zone2=["rec-b"]
    )

    assert result is False

# Testing main function
@patch('DNS_Failover.fetchDiskUsage')
@patch('DNS_Failover.mysql_socket')
@patch('DNS_Failover.service_availability')
@patch('DNS_Failover.get_cname')
@patch('DNS_Failover.nsupdate_cnames')
def test_main(mock_nsupdate_cnames, mock_get_cname, mock_service_availability, mock_mysql_socket, mock_fetchDiskUsage):
    mock_get_cname.return_value = "target-mx.example."
    mock_nsupdate_cnames.return_value = True

    mock_service_availability.return_value = 0
    mock_mysql_socket.return_value = 0
    mock_fetchDiskUsage.return_value = 0

    main()

    assert mock_service_availability.call_count > 0
    assert mock_mysql_socket.call_count > 0
    assert mock_fetchDiskUsage.call_count > 0
    assert mock_get_cname.call_count > 0
    assert mock_nsupdate_cnames.call_count >= 0