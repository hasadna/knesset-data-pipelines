# required for health check
location = / {
    return 200 'it works!';
    add_header Content-Type text/plain;
}
