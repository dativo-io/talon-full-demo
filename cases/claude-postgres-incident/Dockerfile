FROM node:22.16.0-bookworm-slim
WORKDIR /opt/incident
COPY package.json ./
RUN npm install --omit=dev --ignore-scripts --no-audit --no-fund
COPY src/ ./src/
USER node
CMD ["node", "--experimental-strip-types", "src/app.ts"]
