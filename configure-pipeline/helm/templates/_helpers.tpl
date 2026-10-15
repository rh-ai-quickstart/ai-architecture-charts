{{/*
Expand the name of the chart.
*/}}
{{- define "configure-pipeline.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Resolve storage once for DSPA, notebook credentials, and connection endpoints.
Use the dependency's own naming helpers so overrides and release naming agree.
*/}}
{{- define "configure-pipeline.storage" -}}
{{- $storage := deepCopy .Values.pipelineStorage.externalStorage -}}
{{- if (index .Values "aws-compatible-storage").enabled -}}
{{- $bundled := index .Subcharts "aws-compatible-storage" -}}
{{- $_ := set $storage "host" (printf "%s.%s.svc.cluster.local" (include "aws-compatible-storage.fullname" $bundled) .Release.Namespace) -}}
{{- $_ := set $storage "port" (toString $bundled.Values.service.s3Port) -}}
{{- $_ := set $storage "scheme" "http" -}}
{{- $_ := set $storage "s3CredentialsSecret" (dict "secretName" (include "aws-compatible-storage.secretName" $bundled) "accessKey" "AWS_ACCESS_KEY_ID" "secretKey" "AWS_SECRET_ACCESS_KEY") -}}
{{- else -}}
{{- $_ := required "pipelineStorage.externalStorage.host is required when aws-compatible-storage.enabled=false" $storage.host -}}
{{- $_ := required "pipelineStorage.externalStorage.s3CredentialsSecret.secretName is required when aws-compatible-storage.enabled=false" $storage.s3CredentialsSecret.secretName -}}
{{- end -}}
{{- toYaml $storage -}}
{{- end -}}

{{- define "configure-pipeline.storageEndpoint" -}}
{{- $storage := include "configure-pipeline.storage" . | fromYaml -}}
{{- printf "%s://%s:%s" $storage.scheme $storage.host (toString $storage.port) -}}
{{- end -}}
