ARG NODE_VERSION=22-alpine
FROM node:${NODE_VERSION} AS build

WORKDIR /app

RUN npm install -g npm@11

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# CRA inlines REACT_APP_* vars at build time; they must be present here.
ARG REACT_APP_SUPABASE_URL
ARG REACT_APP_SUPABASE_ANON_KEY
ENV REACT_APP_SUPABASE_URL=$REACT_APP_SUPABASE_URL
ENV REACT_APP_SUPABASE_ANON_KEY=$REACT_APP_SUPABASE_ANON_KEY

RUN npm run build

FROM nginx:alpine AS frontend

COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
