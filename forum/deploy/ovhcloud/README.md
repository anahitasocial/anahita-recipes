# The server at OVHcloud

A VPS in Beauharnois, Quebec, ordered in OVHcloud's control panel. **Not
tried yet with Anahita:** tell us how it went, in an
[issue](https://github.com/anahitasocial/anahita-recipes/issues).

1. In the control panel, order a **VPS** with at least 2 vCores, 4 GB of
   memory and 40 GB of disk. Choose **Beauharnois** (Canada) as its place,
   **Ubuntu 24.04** as its system, and add your SSH public key.
2. When it is ready, its address (IPv4) is on the VPS's page, and the user
   to sign in as is **ubuntu**. Try it: `ssh ubuntu@<address>`.
3. Shut everything out but SSH, 80 and 443, with the **Network Firewall** on
   the VPS's IP address (in the control panel, under the IP): allow TCP on
   22, 80 and 443, and established connections, then refuse the rest.
   OVHcloud's [Securing a VPS](https://docs.ovhcloud.com/en/guides/bare-metal-cloud/virtual-private-servers/secure-your-vps)
   says how.
4. Point the five DNS names at the address ([../README.md](../README.md)).
5. Then, from the recipe's folder: `make init`, giving `ubuntu` as the
   user, and `make server`.

For daily copies of the whole server, OVHcloud sells **Automated Backup**
for a VPS. The database is copied every night into the site's files
whatever you choose (`make backup` does it at once).
