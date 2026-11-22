FROM nginx:1.30.7@sha256:7fad6c0dff97965adbddf28027d934b111fc0221a554315dc274712f3fba24d3
COPY docker/nginx.conf /etc/nginx/nginx.conf
