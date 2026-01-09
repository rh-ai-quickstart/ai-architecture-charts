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

{{/* PostgreSQL fullname - matches what the pgvector subchart creates */}}
{{- define "model-registry.postgres.fullname" -}}
{{- .Values.postgres.name | default "pgvector-model-registry" }}
{{- end }}

{{/* PostgreSQL namespace */}}
{{- define "model-registry.postgres.namespace" -}}
{{- .Values.postgres.namespace | default .Release.Namespace }}
{{- end }}

{{/* PostgreSQL host with namespace (FQDN for cross-namespace access) */}}
{{- define "model-registry.postgres.host" -}}
{{- printf "%s.%s.svc.cluster.local" (include "model-registry.postgres.fullname" .) (include "model-registry.postgres.namespace" .) }}
{{- end }}

{{/* PostgreSQL connection string */}}
{{- define "model-registry.postgres.connectionString" -}}
{{- printf "postgresql://%s:%s@%s:%d/%s" .Values.postgres.user .Values.postgres.password (include "model-registry.postgres.host" .) (.Values.postgres.port | default 5432 | int) .Values.postgres.database }}
{{- end }}

{{/* PostgreSQL secret name */}}
{{- define "model-registry.postgres.secretName" -}}
{{- include "model-registry.postgres.fullname" . }}
{{- end }}

