{{- define "app-common-env" -}}
- {name: DPP_DB_ENGINE, valueFrom: {secretKeyRef: {name: {{.Values.global.secretEnvVars | quote}}, key: "DPP_DB_ENGINE"}}}
- {name: DPP_REDIS_HOST, value: "redis"}
- {name: DPP_WORKER_CONCURRENCY, value: {{.Values.dppWorkerConcurrency | default "1" | quote}}}
- {name: S3_ENDPOINT_URL, valueFrom: {secretKeyRef: {name: {{.Values.global.secretEnvVars | quote}}, key: "S3_ENDPOINT_URL"}}}
- {name: AWS_ACCESS_KEY_ID, valueFrom: {secretKeyRef: {name: {{.Values.global.secretEnvVars | quote}}, key: "AWS_ACCESS_KEY_ID"}}}
- {name: AWS_SECRET_ACCESS_KEY, valueFrom: {secretKeyRef: {name: {{.Values.global.secretEnvVars | quote}}, key: "AWS_SECRET_ACCESS_KEY"}}}
- {name: RTF_EXTRACTOR_BIN, value: "/knesset/bin/rtf_extractor.py"}
{{ if .Values.influxDb }}- {name: DPP_INFLUXDB_URL, value: "http://influxdb:8086"}
- {name: DPP_INFLUXDB_DB, value: {{.Values.influxDb | quote}}}{{ end }}
{{- end -}}
