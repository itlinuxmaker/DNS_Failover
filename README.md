# DNS_Failover

**Version**: 1.3.1
**Author**: Andreas Günther ([github@it-linuxmaker.com](mailto:github@it-linuxmaker.com))  
**License**: GNU General Public License v3.0 or later

---

## Project Description

`DNS_Failover` is a Python script that automatically performs DNS failover by updating CNAME records when critical services on a mail server become unreachable.

This script is part of the redundant mail server concept described in detail at [https://www.linuxmaker.com](https://www.linuxmaker.com/linux/redundanter-mailserver.html).

> **Important:**  
> This failover program is specifically designed to run on **Linux systems**.  
> Compatibility with Windows or other operating systems has **not** been tested or considered.

---

## Purpose

The script is intended to be installed **directly on the Bind9 DNS server** and executed regularly via a **cron job**. It monitors multiple services on two mail servers and automatically updates the relevant DNS CNAME records using `nsupdate` when a failure is detected.  
Additionally, the MySQL socket is checked for its existence and the storage capacity of the partition containing the movable server files is queried. Both of these actions can lead to a mail system failure.

This ensures seamless service continuity by redirecting traffic to a backup mail server.

---

## How It Works

1. Checks the availability of the following services on two mail servers:
   - SMTP (port 25)
   - IMAPS (port 993)
   - HTTPS (port 443)
   - MySQL (port 3306)
   
2. Checks MySQL socket availability and memory capacity

3. If a service is unreachable on one server:
   - Logs the failure
   - Performs DNS failover by updating CNAME records to point to the backup server
4. When the primary server becomes reachable again, the DNS records are restored automatically.
5. If an nsupdate is triggered, i.e. one of the mail servers is not reachable, an email is sent to the person entered in the config (since version 1.3.0).

---

## Installation & Configuration

### Where to Install?

The script **must be installed and run directly on the Bind9 DNS server**, as it performs DNS updates locally via `nsupdate`.

The script monitors the following DNS records:

* `mx`
* `smtp`
* `imap`
* `mail`
* `pop3`

---

### Dependencies

* Python 3
* `dnspython` module
* `paramiko` module

Install dependencies via pip:

```
pip install dnspython
pip install paramiko
```

---
## Installation and Setup
### 1. Create the configuration directory and set the file permissions
The program expects the configuration file under */usr/local/etc/dnsfailover/*

```
sudo mkdir -p /usr/local/etc/dnsfailover
```
```
sudo cp DNS_Failover/config/config.cfg /usr/local/etc/dnsfailover/
```

```
sudo chown root:root /usr/local/etc/dnsfailover/config.cfg
sudo chmod 600 /usr/local/etc/dnsfailover/config.cfg
```

**Note:** The file contains configuration data and should only be readable by root.

### 2. Adjust the configuration values ​​by opening the file with an editor of your choice:

```  
sudo nano /usr/local/etc/dnsfailover/config.cfg
```
or

```  
sudo vim /usr/local/etc/dnsfailover/config.cfg  
  ```
  
  **Note:** Adjust the values ​​like zone1, mxip1, user, ttl, etc. to your environment.
  
```
[ZONES]
zone1 = domain1.tld
zone2 = domain2.tld

[MX]
mxip1 = 1.2.3.4
mxip2 = 1.2.3.5
mx1 = mx1.example.com
mx2 = mx2.example.com

[RECORDS]
record_mx = mx
record_smtp = smtp
record_imap = imap
record_mail = mail
record_pop3 = pop3

[PORTS]
smtp = 25
imaps = 993
https = 443
mysql = 3306
port1 = 22
port2 = 22

[SETTINGS]
ttl = 60
ns = 192.168.0.2
logfile = /var/log/bind/bind.log
space_limit = 97
partition = /var/
user = root
```

### 3. Copying the main program
The Python program *DNS_Failover.py* is copied to */usr/local/bin/*:
```
sudo cp ~/DNS_Failover/DNS_Failover.py /usr/local/bin/
```

You can then run it with
```
sudo python3 /usr/local/bin/DNS_Failover.py
```

### 4. Preparing SSH access to mail servers with public key authentication
 
Access to the mail servers involved via SSH is essential for the functionality of this program.
* **SSH access** from the local to the remote host.
* **Public key authentication** (SSH key) for the root user without password prompt.
* **SSH key of the root user** on the local system (e.g. in *~/.ssh/id_rsa*).
* **Remote host accepts the key** in *~/.ssh/authorized_keys* of the root user.
* **SSH access for root on the remote host is allowed** (in */etc/ssh/sshd_config: PermitRootLogin yes*).

You can also see a complete guide on setting up public key authentication at https://www.linuxmaker.com/en/how-to/ssh-login-without-password.html.

## Scheduled Execution via Cron

To run the script regularly (e.g., every 5 minutes), add a cron job entry by running:

```
crontab -e
```

Add the following line (adjust the path to your script accordingly):

```
*/5 * * * * /usr/bin/python3 /usr/local/bin/DNS_failover.py
```

---

## Logging

All actions and errors are logged to the file `/var/log/bind/bind.log` by default.

Sample log output:

```
07.09.2025 12:01:02 [INFO    ] [main] ==== Start DNS-Failover ====
07.09.2025 12:01:03 [ERROR   ] [port_check] The port 25 on the host 1.2.3.4 is not reachable.
07.09.2025 12:01:06 [INFO    ] [main] ==== DNS-Failover has been completed ====
```

---

## Further Information

Detailed documentation of the redundant mail server concept can be found at:
[https://www.linuxmaker.com/linux/redundanter-mailserver.html](https://www.linuxmaker.com/linux/redundanter-mailserver.html)

---

## License

This project is licensed under the **GNU General Public License v3.0 or later**.
See [https://www.gnu.org/licenses/gpl-3.0.html](https://www.gnu.org/licenses/gpl-3.0.html) for details.

---

## Contact

For questions, bug reports, or suggestions:

* Email: [github@it-linuxmaker.com](mailto:github@it-linuxmaker.com)
* Or open an issue or pull request here on GitHub.

```
