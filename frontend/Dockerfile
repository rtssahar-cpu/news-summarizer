FROM node:24-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM deps AS dev
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM deps AS test
COPY . .
RUN npm run lint && npm run build

FROM nginx:alpine AS production
COPY --from=test /app/dist /usr/share/nginx/html
EXPOSE 80
