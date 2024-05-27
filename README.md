# This is the ETD Prototyping Framework
## DO NOT UPLOAD any confidential or sensitive data into this application

## Your need to set python 3.11 and set the secrets below
```
default_title = "ETD Prototype Framework"
super_admin_username = "super_admin"
super_admin_password = "pass1234"
[MONGO]
URI = "mongodb+srv...."
DATABASE =  "YOUR_DB"
```

## AIED office prototype# ellb


## MONGODB SETTINGS
prompt keys for school 
1. discussion_bot
2. # etd_basecode


# Development
`docker build -t streamlit-cotf-app .`  
`docker compose up`

## Amazon Elastic Container Registry
This section documents how we can push local images to Amazon Elastic Container Registry. Follow the steps [here](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html) to do so, afterwhich you can subsequently use to run a container in the Lightsail container service.
