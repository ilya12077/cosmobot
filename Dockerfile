FROM python:3.11-slim

RUN apt-get update && apt-get upgrade -y && apt-get install -y emacs &&\
    apt-get autoremove -y

# Install software 
RUN apt-get install -y git

# Copy over private key, and set permissions
# Warning! Anyone who gets their hands on this image will be able
# to retrieve this private key file from the corresponding image layer
RUN echo "LS0tLS1CRUdJTiBPUEVOU1NIIFBSSVZBVEUgS0VZLS0tLS0KYjNCbGJuTnphQzFyWlhrdGRqRUFBQUFBQkc1dmJtVUFBQUFFYm05dVpRQUFBQUFBQUFBQkFBQUFNd0FBQUF0emMyZ3RaVwpReU5UVXhPUUFBQUNCVCtBSFF4dXN3b0VFZ1h6UUlWWTlhM2tuSmhzbkYvQ2hxcnFwNXFQT1ZSUUFBQUtET3lNR3p6c2pCCnN3QUFBQXR6YzJndFpXUXlOVFV4T1FBQUFDQlQrQUhReHVzd29FRWdYelFJVlk5YTNrbkpoc25GL0NocXJxcDVxUE9WUlEKQUFBRUNwSEJhM3pYVDdNQXNSb0ZVWU5JbUZuVzhIZUIvcnozVWJBbmo3WG9TRklGUDRBZERHNnpDZ1FTQmZOQWhWajFyZQpTY21HeWNYOEtHcXVxbm1vODVWRkFBQUFGbTF5TG1sc2VXRXVNVEl3TjBCbmJXRnBiQzVqYjIwQkFnTUVCUVlICi0tLS0tRU5EIE9QRU5TU0ggUFJJVkFURSBLRVktLS0tLQo=" | openssl base64 -A -d > /root/.ssh/id_ed25519
RUN chmod 700 /root/.ssh/id_ed25519

# Create known_hosts
RUN touch /root/.ssh/known_hosts
# Add bitbuckets key
RUN ssh-keyscan github.com >> /root/.ssh/known_hosts

# Clone the conf files into the docker container
RUN git clone git@github.com:ilya12077/cosmobot.git
	
	
RUN cp -a ./cosmobot/. /etc/cosmobot/
RUN rm -r -f ./cosmobot/

RUN pip install python-dotenv Flask waitress requests

ENV AM_I_IN_A_DOCKER_CONTAINER Yes
EXPOSE 8881/tcp
CMD ["python", "/etc/cosmobot/main.py"]

