FROM nodered/node-red:3.1.9
RUN npm install node-red-dashboard node-red-node-mongodb
COPY flows.json /data/flows.json
COPY settings.js /data/settings.js
