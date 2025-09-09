# DNS_Failover

**Version**: 1.0.0  
**Author**: Andreas Günther ([github@it-linuxmaker.com](mailto:github@it-linuxmaker.com))  
**License**: GNU General Public License v3.0 or later

---

## Project Description

`DNS_Failover` is a Python script that automatically performs DNS failover by updating CNAME records when critical services on a mail server become unreachable.

This script is part of the redundant mail server concept described in detail at [https://www.linuxmaker.com](https://www.linuxmaker.com/linux/redundanter-mailserver.html).

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
   - MySQL-Socket
   - Storage capacity of var-partition
2. If a service is unreachable on one server:
   - Logs the failure
   - Performs DNS failover by updating CNAME records to point to the backup server
3. When the primary server becomes reachable again, the DNS records are restored automatically.

---

## Installation & Configuration

### Where to Install?

The script **must be installed and run directly on the Bind9 DNS server**, as it performs DNS updates locally via `nsupdate`.

### Configuration

All configuration parameters are set at the top of the script, for example:

```python
zone1 = "domain1.tld"
zone2 = "domain2.tld"

mxip1 = "1.2.3.4"  # IP of mail server 1
mxip2 = "1.2.3.5"  # IP of mail server 2

mx1 = "mx1.example.com"
mx2 = "mx2.example.com"

ttl = 60           # DNS record TTL in seconds
ns = "192.168.0.2" # IP address of the Bind9 DNS server
````

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

Install dependencies via pip:

```bash
pip install dnspython
```

---

## Scheduled Execution via Cron

To run the script regularly (e.g., every 5 minutes), add a cron job entry by running:

```bash
crontab -e
```

Add the following line (adjust the path to your script accordingly):

```cron
*/5 * * * * /usr/bin/python3 /path/to/dns_failover.py
```

---

## Logging

All actions and errors are logged to the file `DNS-Failovertest.log` by default.

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