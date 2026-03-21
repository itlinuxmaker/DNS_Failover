# DNS_Failover

**Version**: 1.4.2
**Author**: Andreas Günther ([github@it-linuxmaker.com](mailto:github@it-linuxmaker.com))  
**License**: GNU General Public License v3.0 or later

---

## Project Description

`DNS_Failover` is a Python-based program that automatically performs DNS failover by updating CNAME records via RFC 2136 when critical services on a mail server (such as SMTP, IMAP, HTTPS, or MySQL) become unreachable.
It is designed for Linux-based infrastructures using Postfix, Dovecot, and BIND, and ensures high availability by dynamically redirecting mail traffic to a standby server.

This program is part of the redundant mail server concept described in detail at [https://www.linuxmaker.com](https://www.linuxmaker.com/linux/redundanter-mailserver.html).

> **Important:**  
> This failover program is specifically designed to run on **Linux systems**.  
> Compatibility with Windows or other operating systems has **not** been tested or considered.

---

## Purpose

The program is intended to be installed **directly on the Bind9 DNS server** and executed regularly via a **cron job** or with a **systemd timer** as **systemd unit**. It monitors multiple services on two mail servers and automatically updates the relevant DNS CNAME records using `nsupdate` when a failure is detected.  
Additionally, the MySQL socket is checked for its existence and the storage capacity of the partition containing the movable server files is queried. Both of these actions can lead to a mail system failure.

With version 1.4.0, the program calls the external Bash script `HD_fsck.sh` via `fsck -n`. This tests the vmail partition on the mail server for corrupted inodes.

If an nsupdate is triggered, i.e. one of the mail servers is not reachable, an email notification is sent to the address configured in the `[MAIL]` section of the configuration file (since version 1.3.0).

This ensures seamless service continuity by redirecting traffic to a backup mail server.

---

## How It Works

1. Checks the availability of the following services on two mail servers:
   - SMTP (port 25)
   - IMAPS (port 993)
   - HTTPS (port 443)
   - MySQL (port 3306)

2. Checks MySQL socket availability and memory capacity.
3. Checks the vmail partition of the mail server for faulty inodes (via `HD_fsck.sh`, since v1.4.0).
4. If a service is unreachable on one server:
   - Logs the failure
   - Performs DNS failover by updating CNAME records to point to the backup server
   - Sends an email notification to the configured recipient (since v1.3.0)
5. When the primary server becomes reachable again, the DNS records are restored automatically.

---

## Installation & Configuration

### Where to Install?

The program **must be installed and run directly on the Bind9 DNS server**, as it performs DNS updates locally via `nsupdate`.

The program monitors the following DNS records:

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
* `smtplib` (part of the Python standard library – no separate installation required)

Install dependencies via pip:

```
pip install dnspython
pip install paramiko
```

---

## Installation and Setup

### 1. Create the configuration directory and set the file permissions

The program expects the configuration file under `/usr/local/etc/dnsfailover/`

```
sudo mkdir -p /usr/local/etc/dnsfailover
```

```
sudo cp DNS_Failover/config/config.cfg /usr/local/etc/dnsfailover/
```

**Since v1.4.0** – copy and enable the inode check script:

```
sudo cp DNS_Failover/HD_fsck.sh /usr/local/bin/
sudo chmod a+x /usr/local/bin/HD_fsck.sh
```

```
sudo chown root:root /usr/local/etc/dnsfailover/config.cfg
sudo chmod 600 /usr/local/etc/dnsfailover/config.cfg
```

**Note:** The file contains configuration data and should only be readable by root.

### 2. Adjust the configuration values by opening the file with an editor of your choice:

```  
sudo nano /usr/local/etc/dnsfailover/config.cfg
```

or

```  
sudo vim /usr/local/etc/dnsfailover/config.cfg  
```

**Note:** Adjust the values like zone1, mxip1, user, ttl, etc. to your environment.

```ini
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

[MAIL]
sender_email = noreply@example.com
recipient_email = admin@example.com
mx_server = smtp.example.com
port = 587
use_tls = false
username =
password =
```

> **Note on `[MAIL]`:** The `username` and `password` fields can be left empty if the mail server does not require authentication. Set `use_tls = true` if STARTTLS is required.

### 3. Copying the main program

The Python program `DNS_Failover.py` is copied to `/usr/local/bin/`:

```
sudo cp ~/DNS_Failover/DNS_Failover.py /usr/local/bin/
```

You can then run it with:

```
sudo python3 /usr/local/bin/DNS_Failover.py
```

### 4. Preparing SSH access to mail servers with public key authentication

Access to the mail servers involved via SSH is essential for the functionality of this program.

* **SSH access** from the local to the remote host.
* **Public key authentication** (SSH key) for the root user without password prompt.
* **SSH key of the root user** on the local system (e.g. in `~/.ssh/id_rsa`).
* **Remote host accepts the key** in `~/.ssh/authorized_keys` of the root user.
* **SSH access for root on the remote host is allowed** (in `/etc/ssh/sshd_config: PermitRootLogin yes`).

You can also see a complete guide on setting up public key authentication at https://www.linuxmaker.com/en/how-to/ssh-login-without-password.html.

### 5. Running the Tests

The test suite is located in the `tests/` directory and requires a dedicated test configuration file at `tests/config/config.cfg`. This file mirrors the structure of the production configuration but uses safe placeholder values – no real credentials or live infrastructure is needed.

Before running the tests, activate the virtual environment:
```bash
source venv/bin/activate
```

To run the full test suite, execute the following command from the project root directory:
```bash
DNSFAILOVER_CONFIG=tests/config/config.cfg pytest tests/ -v
```

The environment variable `DNSFAILOVER_CONFIG` overrides the default configuration path so that the program loads the test configuration instead of the production file at `/usr/local/etc/dnsfailover/config.cfg`.

The `-v` flag enables verbose output, showing each individual test case with its result.

### Requirements

Before running the tests, ensure the following packages are installed inside the virtual environment:
```
pip install pytest dnspython paramiko
```

---

## Scheduled Execution via Systemd-Timer

To run the program regularly (e.g., every 10 minutes), create a systemd timer and service using:

```
# vi /etc/systemd/system/DNS-Failover.timer
[Unit]
Description=Timer for DNS-Failover service

[Timer]
OnCalendar=*-*-* *:00,20,40:00
Unit=DNS-Failover.service

[Install]
WantedBy=timers.target

```

And as systemd service:
```
# vi /etc/systemd/system/DNS-Failover.service
[Unit]
Description=Service for DNS-Failover

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /usr/local/bin/DNS_Failover.py

[Install]
WantedBy=multi-user.target

```

To activate and start the timer, execute the following:
```
# systemctl daemon-reload  
# systemctl enable DNS-Failover.timer  
# systemctl start DNS-Failover.timer  
# systemctl list-timers DNS-Failover.timer
```

---
## DNS zone file - TTL

The cron job running every 10 minutes is a deliberate compromise between response speed and system load. In the event of a service outage with a TTL of 300 seconds, the new DNS entry will be available a maximum of 15 minutes later. Since mail servers attempt delivery more than once, and SMTP sending is also restored after 15 minutes, this is perfectly acceptable.

---

## Logging

All actions and errors are logged to the file `/var/log/dns-failover.log` by default.

Sample log output:

```
07.09.2025 12:01:02 [INFO    ] [main] ==== Start DNS-Failover ====
07.09.2025 12:01:03 [ERROR   ] [port_check] The port 25 on the host 1.2.3.4 is not reachable.
07.09.2025 12:01:06 [INFO    ] [main] ==== DNS-Failover has been completed ====
```

---

## System Requirements and Platform Notice

**DNS-Failover is designed exclusively for use in Linux/Unix-based** mail server environments.
The program performs checks and failover operations on services that are **not available or not supported** in the same way on Microsoft Windows.

### Required Services (must be running on the target mail servers):

* BIND as the authoritative DNS server (must support nsupdate per RFC 2136)
* Postfix as the Mail Transfer Agent (SMTP)
* Dovecot for IMAP/POP3 access
* MySQL with local UNIX socket (`/var/run/mysqld/mysqld.sock`)
* SSH access to the mail servers (for remote checks)

### Not supported:

* Windows-based mail servers (e.g. Microsoft Exchange)
* Windows DNS servers (do not support `nsupdate` in RFC 2136 format)
* Environments without SSH or POSIX-compatible shell access

**Note:** While the program can technically be executed on Windows (with Python installed), it will **not function correctly** unless the required Linux services are available on the target infrastructure.

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
