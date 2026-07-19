FROM node AS build

COPY . .
run npm install

FROM build as frontend
EXPOSE 5000
CMD ["npm", "run"]