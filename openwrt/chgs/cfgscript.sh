#!/bin/sh
# TinajaLabs, Summer 2012
# The /opt/chgs directory on the thumb drive contains a set of config files 
# for a default tinaja labs install.
# Once the thumb drive has been established through the web interface,
# this script should do the rest.

echo "copy standard thumb drive config files to /etc"
cp -r /opt/chgs/etc/* /etc

# change to the /etc directory and show the banner file
cd /etc
cat banner

echo "Done... if you see the TinajaLabs logon banner."
echo "Reboot to see the changes take effect..."
