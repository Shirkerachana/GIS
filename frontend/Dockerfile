FROM node:20-alpine

WORKDIR /app

COPY frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/tailwind.config.js frontend/postcss.config.js /app/frontend/
COPY frontend/index.html /app/frontend/index.html
COPY frontend/src /app/frontend/src

WORKDIR /app/frontend
RUN npm install

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

