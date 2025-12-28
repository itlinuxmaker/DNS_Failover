#!/bin/bash
# The script executes fsck in read-only mode to test the mailbox partition on
# the mail server for inode errors. If an error is found, it returns a value
# of 1 to DNS_Failover.

DEVICE="/dev/vda"

fsck_output=$(fsck -n "$DEVICE" 2>&1)

if echo "$fsck_output" | grep -E -q "(deleted inode|bitmap differences)"; then
    echo "1"
else
    echo "0"
fi