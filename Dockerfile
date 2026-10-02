FROM nginx:alpine

# Upgrade OS packages to patch vulnerabilities
RUN apk upgrade --no-cache

# Remove default nginx static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy custom NGINX configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy Nexvion frontend application workload static files
COPY index.html /usr/share/nginx/html/
COPY products.html /usr/share/nginx/html/
COPY payment.html /usr/share/nginx/html/
COPY style.css /usr/share/nginx/html/
COPY products.css /usr/share/nginx/html/
COPY payment.css /usr/share/nginx/html/
COPY script.js /usr/share/nginx/html/
COPY payment.js /usr/share/nginx/html/
COPY logo.png /usr/share/nginx/html/

# Adjust directory permissions for non-root NGINX execution
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx /tmp && \
    chmod -R 755 /usr/share/nginx/html

# Switch to non-root user (UID 101 in alpine)
USER nginx

# Expose HTTP port 80
EXPOSE 80

# Container healthcheck targeting /healthz
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://127.0.0.1:80/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]