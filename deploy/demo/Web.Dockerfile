FROM nginx:1.27.5-alpine

COPY deploy/demo/nginx.conf /etc/nginx/nginx.conf
COPY web/index.html /usr/share/nginx/html/index.html

EXPOSE 8080
ENTRYPOINT ["nginx", "-g", "daemon off;"]
