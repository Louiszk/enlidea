FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
# Use BuildKit cache for npm
RUN --mount=type=cache,target=/root/.npm npm install

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
