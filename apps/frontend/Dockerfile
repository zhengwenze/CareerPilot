FROM node:20-alpine AS base

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci --frozen-lockfile

COPY . .

FROM node:20-alpine AS development

WORKDIR /app

COPY --from=base /app/node_modules ./node_modules
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]

FROM node:20-alpine AS production

WORKDIR /app

COPY --from=base /app/node_modules ./node_modules
COPY . .

ENV NODE_ENV=production

RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
