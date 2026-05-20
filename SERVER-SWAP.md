# Server Swap Setup

The server (138.197.178.190) has only 3.8GB RAM which runs out during Next.js builds.
A 2GB swap file was added to prevent build hangs.

## If swap is gone after server restart, re-add it:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Verify swap is active:
```bash
free -h
```
Should show `Swap: 2.0Gi` under the Swap row.

## Make swap permanent (survives reboots):
```bash
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Build command to use with swap:
```bash
cd /var/www/saie-frontend && NODE_OPTIONS="--max-old-space-size=3072" npm run build && pm2 restart 2
```
