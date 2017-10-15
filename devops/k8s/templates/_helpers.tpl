{{- define "app-workers-anti-affinity" -}}
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchExpressions:
        - key: app
          operator: In
          values: ["app-workers"]
      topologyKey: "kubernetes.io/hostname"
{{- end -}}

{{- define "shared-host-affinity" -}}
podAffinity:
  requiredDuringSchedulingIgnoredDuringExecution:
  - labelSelector:
      matchExpressions:
      - key: app
        operator: In
        values: ["nginx"]
    topologyKey: "kubernetes.io/hostname"
{{- end -}}
