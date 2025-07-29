brew services restart mongodb-community

mongod --config /usr/local/etc/mongod.conf -fork

cfg = rs.conf()
cfg.members[0].host = "host.docker.internal:27017"
rs.reconfig(cfg, { force: true })


docker build -t codegen .
docker run -p 8000:8000 \
  --rm\
  --add-host=host.docker.internal:host-gateway \
  -e MONGO_HOST=host.docker.internal \
  -e MONGO_PORT=27017 \
  -e MONGO_DB=policy_system \
  -e MONGO_REPLICA_SET=rs0 \
  codegen

npm create vite@latest policy-ui -- --template react
npm run dev

uvcorn 