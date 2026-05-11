FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package.json .

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the app
RUN npm run build

# Use nginx to serve the built files
FROM nginx:alpine

# Copy built files to nginx
COPY --from=0 /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]