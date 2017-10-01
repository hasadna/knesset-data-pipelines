# pipelines data in html format - for humans
location /data/ {
    autoindex on;
    autoindex_exact_size off;
    autoindex_format html;
    autoindex_localtime on;
    alias /knesset-data-pipelines/;
    charset utf-8;
}

# pipelines data in json format - for scraping
location /data-json/ {
    autoindex on;
    autoindex_exact_size on;
    autoindex_format json;
    autoindex_localtime off;
    alias /knesset-data-pipelines/;
    charset utf-8;
}
