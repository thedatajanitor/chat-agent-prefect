FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json ./
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Default to dev mode (can be overridden in docker-compose)
CMD ["npm", "run", "dev"]