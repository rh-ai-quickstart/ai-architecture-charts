{{/* Expand the name of the chart. */}}
{{- define "model-registry.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Create a default fully qualified app name. */}}
{{- define "model-registry.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/* Create chart name and version as used by the chart label. */}}
{{- define "model-registry.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/* Common labels */}}
{{- define "model-registry.labels" -}}
helm.sh/chart: {{ include "model-registry.chart" . }}
{{ include "model-registry.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/* Selector labels */}}
{{- define "model-registry.selectorLabels" -}}
app.kubernetes.io/name: {{ include "model-registry.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/* Model Registry resource name */}}
{{- define "model-registry.resourceName" -}}
{{- .Values.name | default (include "model-registry.fullname" .) }}
{{- end }}

{{/* Model Registry namespace */}}
{{- define "model-registry.namespace" -}}
{{- .Values.namespace | default .Release.Namespace }}
{{- end }}

{{/* MySQL fullname - matches what the mysql subchart creates */}}
{{- define "model-registry.mysql.fullname" -}}
{{- .Values.mysql.name | default "mysql" }}
{{- end }}

{{/* MySQL namespace */}}
{{- define "model-registry.mysql.namespace" -}}
{{- .Values.mysql.namespace | default .Release.Namespace }}
{{- end }}

{{/* MySQL host with namespace (FQDN for cross-namespace access) */}}
{{- define "model-registry.mysql.host" -}}
{{- printf "%s.%s.svc.cluster.local" (include "model-registry.mysql.fullname" .) (include "model-registry.mysql.namespace" .) }}
{{- end }}

{{/* MySQL connection string */}}
{{- define "model-registry.mysql.connectionString" -}}
{{- printf "mysql://%s:%s@%s:%d/%s" .Values.mysql.user .Values.mysql.password (include "model-registry.mysql.host" .) (.Values.mysql.port | default 3306 | int) .Values.mysql.database }}
{{- end }}

{{/* MySQL secret name */}}
{{- define "model-registry.mysql.secretName" -}}
{{- include "model-registry.mysql.fullname" . }}
{{- end }}

