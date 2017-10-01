# let's encrypt authentication challenge
location /.well-known/ {
    alias /usr/share/nginx/html/.well-known/;
}
