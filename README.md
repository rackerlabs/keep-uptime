# Keep Uptime Agent

This agent is meant to be distributed on multiple systems to give an accurate representation of the availability of the Cloud Keep service.

## Example Config

```
[DEFAULT]
username      = username
api_key       = api_key
regions       = ["IAD", "ORD", "LON"]
interval      = 10
statsd_server = statsd.server
```
