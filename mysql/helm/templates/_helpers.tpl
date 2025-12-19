{{/*
Expand the name of the chart.
*/}}
{{- define "mysql.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "mysql.fullname" -}}
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

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "mysql.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "mysql.labels" -}}
helm.sh/chart: {{ include "mysql.chart" . }}
{{ include "mysql.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "mysql.selectorLabels" -}}
app.kubernetes.io/name: {{ include "mysql.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
MySQL resource name - uses name from values or fullname
*/}}
{{- define "mysql.resourceName" -}}
{{- .Values.name | default (include "mysql.fullname" .) }}
{{- end }}

{{/*
MySQL namespace - uses namespace from values or release namespace
*/}}
{{- define "mysql.namespace" -}}
{{- .Values.namespace | default .Release.Namespace }}
{{- end }}

{{/*
MySQL host with namespace (FQDN for cross-namespace access)
*/}}
{{- define "mysql.host" -}}
{{- printf "%s.%s.svc.cluster.local" (include "mysql.resourceName" .) (include "mysql.namespace" .) }}
{{- end }}

{{/*
MySQL connection string
*/}}
{{- define "mysql.connectionString" -}}
{{- printf "mysql://%s:%s@%s:%d/%s" .Values.user .Values.password (include "mysql.host" .) (.Values.port | default 3306 | int) .Values.database }}
{{- end }}

{{/*
MySQL secret name
*/}}
{{- define "mysql.secretName" -}}
{{- include "mysql.resourceName" . }}
{{- end }}

